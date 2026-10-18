import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BOT_NAME = "SanjeebSpider"
USER_AGENT = f"{BOT_NAME}/v1.0 (sanjibpoudel49@gmail.com)"
DEFAULT_DELAY = 2.0
MAX_PAGES = 20
OUTPUT_FILE = 'urls.txt'
ALLOWED_SCHEMES = {'http', 'https'}

SEEDS = [
    'https://en.wikipedia.org/wiki/Main_Page',
    'https://www.gutenberg.org',
    'https://developer.mozilla.org',
    'https://docs.python.org'
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

with open(OUTPUT_FILE, 'w') as out:
    
    while queue and len(visited) < MAX_PAGES:
        
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
                
            html = response.text # body download
            base_url = response.url
             
        
        except requests.RequestException as e:
            print(f"Error occured for {url} : {e}")
            continue
        
            
        out.write(url + "\n")
        out.flush()
        
        print(f"{len(visited)} : {url}")
        
        soup = BeautifulSoup(html, "html.parser")
        
        for a in soup.find_all('a', href = True):
            
            link, _ = urldefrag(urljoin(base_url, a['href']))
            p = urlparse(link) 
            
            if p.scheme not in ALLOWED_SCHEMES:
                continue
            if p.query:
                continue
            if link in seen:
                continue
            
            dom = (f'{p.scheme}://{p.netloc}')
            
            if dom not in per_domain_count:
                continue
            
            if per_domain_count[dom] >= 1250:
                continue
            
            seen.add(link)
            queue.append(link)
            per_domain_count[dom] += 1