import time
import json
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BOT_NAME = "SanjeebSpider"
USER_AGENT = f"{BOT_NAME}/v1.0 (sanjibpoudel49@gmail.com)"
DEFAULT_DELAY = 2.0
MAX_PAGES = 100 # CHANGE THIS TO 5000
DOMAIN_LIMIT = 25 # AND THIS TO 1250
OUTPUT_FILE = 'pages.jsonl' # AND THIS TO full_pages.jsonl
ALLOWED_SCHEMES = {'http', 'https'}

SEEDS = [ # ADD MORE SEEDS FOR 5000 RUNS GIVEN IN seeds.txt
    'https://en.wikipedia.org/wiki/2026_Nobel_Peace_Prize', #/wiki/
    'https://www.gutenberg.org/ebooks/37683', #/ebooks/
    'https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements', #/en-US/
    'https://docs.python.org/3/tutorial/index.html' # /3/
]



session = requests.Session()
session.headers.update({'User-Agent':USER_AGENT})

robot_cache = {}
last_request = {}

def wait_for_domain(domain, delay):
    elapsed = time.time() - last_request.get(domain , 0) #(domain , 0) meaning domain or 0
    if elapsed < delay:
        time.sleep(delay - elapsed)
    last_request[domain] = time.time()


def get_robots(scheme, domain):
    if domain in robot_cache:
        return robot_cache[domain]
    
    rp = RobotFileParser()
    try:
        wait_for_domain(domain, DEFAULT_DELAY)
        r = session.get(f'{scheme}://{domain}/robots.txt', timeout= 10)
        if r.status_code == 200:
            rp.parse(r.text.splitlines())
        elif r.status_code in (401, 403):
            rp.parse(["User-Agent: *",
                      "Disallow: /"])
        elif 400 <= r.status_code < 500:
            rp.parse([])
        else:
            rp = None
    except requests.RequestException as e:
        print(f"Failed to Parse robots.txt on {domain}, Error: {e}")
        rp = None
        
    robot_cache[domain] = rp
    
    return rp
        
queue = deque(
    SEEDS
)
seen = set(SEEDS)
visited = set()
per_domain_count = {'https://en.wikipedia.org' : 0,
                    'https://www.gutenberg.org' : 0,
                    'https://developer.mozilla.org' : 0,
                    'https://docs.python.org': 0
                    }

doc_id = 0

BLOCKED_EXTENSIONS = ('.pdf', '.zip', '.epub', '.png', '.jpg', '.jpeg',
                      '.gif', '.svg', '.txt', '.xml', '.mp3', '.mp4')


def should_crawl(link):
    p = urlparse(link)
    path = p.path
    domain = p.netloc

    if path.lower().endswith(BLOCKED_EXTENSIONS):
        return False

    if domain == 'en.wikipedia.org':
        if not path.startswith('/wiki/'):
            return False
        title = path[len('/wiki/'):]
        if ':' in title or '%3A' in title.upper():
            return False
        return True

    if domain == 'developer.mozilla.org':
        if '_generator' in path:
            return False
        return path.startswith(('/en-US/docs/', '/en-US/blog/'))

    if domain == 'docs.python.org':
        if not path.startswith('/3/'):
            return False
        if any(bad in path for bad in ('genindex', 'py-modindex', 'search.html',
                                        'download.html', '/_sources/')):
            return False
        return True

    if domain == 'www.gutenberg.org':
        if not path.startswith('/ebooks/'):
            return False
        rest = path[len('/ebooks/'):].strip('/')
        if rest.isdigit():
            return True
        return rest.startswith(('author/', 'subject/', 'bookshelf/'))

    return True


with open(OUTPUT_FILE, 'w', encoding = 'utf-8') as out:
    
    while queue and doc_id < MAX_PAGES:
        
        links = set()
        
        url = queue.popleft()
        
        
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        rp = get_robots(parsed.scheme, domain)
        if rp is None or not rp.can_fetch(BOT_NAME, url):
            continue
        
        delay = max(DEFAULT_DELAY, rp.crawl_delay(BOT_NAME) or 0)
        visited.add(url)
        
        # go to urls
        
        try:
            wait_for_domain(domain, delay)
            response = session.get(url, timeout=10, stream=True)
            
            if response.status_code == 429 or response.status_code == 503:
                print(f"{domain} Going Too Fast skipping {url}")
                response.close()
                continue
            
            content_type = response.headers.get("Content-Type","")
            if response.status_code != 200 or not content_type.startswith("text/html"):
                response.close()
                print(f"Cannot access {domain} and url {url}")
                continue
                
            html = response.content # body download
            base_url = response.url
             
        
        except requests.RequestException as e:
            print(f"Error occured for {url} : {e}")
            continue
        
        print(f"{doc_id+1} : {url}")
        
        soup = BeautifulSoup(html, "html.parser")
        
        data = {}
        
        for a in soup.find_all('a', href = True):
            
            link, _ = urldefrag(urljoin(base_url, a['href']))
            p = urlparse(link) 
            
            
            if p.scheme not in ALLOWED_SCHEMES:
                continue
            if p.query:
                continue
            if not should_crawl(link):
                continue
            
            dom = (f'{p.scheme}://{p.netloc}')
            
            if (dom) in per_domain_count:
                links.add(link)
            
            if link in seen:
                continue
            
            
            if dom not in per_domain_count:
                continue
            
            if per_domain_count[dom] >= DOMAIN_LIMIT:
                continue
            
            
            seen.add(link)
            queue.append(link)
            per_domain_count[dom] += 1
            
        for junk in soup.find_all(['style','script','nav','footer','noscript','template','svg']):
            junk.decompose()
            
        for hidden in soup.find_all(attrs={'aria-hidden':'true'}):
            if not hidden.decomposed:
                hidden.decompose()
        for hidden in soup.find_all(attrs={'hidden':True}):
            if not hidden.decomposed:
                hidden.decompose()
        for junk in soup.select('.navbox, .catlinks, .printfooter'):
            junk.decompose()
            
        title_tag = soup.find('title')
        body_tag = soup.find('body')
        main_tag = soup.find('main')
        article_tag = soup.find('article')
        
        h1_tag = soup.find('h1')
        h2_tag = soup.find('h2')
        h3_tag = soup.find('h3')
        
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            title = ""
            
        h1 = h1_tag.get_text(separator=' ',strip=True) if h1_tag else ""
        
        content_tag = None

        if domain == 'en.wikipedia.org':
            content_tag = soup.find(id='mw-content-text')

        if content_tag is None:
            content_tag = (soup.find(attrs={'role': 'main'})
                           or main_tag or article_tag or body_tag)

        body = content_tag.get_text(separator=' ', strip=True) if content_tag is not None else ''
        
        fetched_time = time.time()
        
        meta_desc = soup.find('meta', attrs={'name':'description'})
        description = meta_desc.get('content','').strip() if meta_desc else ""
        
        meta_keywords = soup.find('meta', attrs={'name':'keywords'})
        keywords = meta_keywords.get('content','').strip() if meta_keywords else ""
        
        doc_id += 1
        
        data['doc_id'] = doc_id
        data['url'] = base_url
        data['domain'] = domain
        data['title'] = title
        data['h1'] = h1
        data['body'] = body
        data['description'] = description
        data['keywords'] = keywords
        data['links'] = sorted(links)
        data['fetched_at'] = fetched_time
        
        json.dump(data, out, ensure_ascii= False)
        out.write("\n")
        out.flush()
        
        