from datetime import datetime, timedelta
import time
from database import Crawl, Product
from parse import Parser


def run_spider():
    while True:
        old_crawlers = Crawl.select().where(Crawl.created_at < (datetime.now() - timedelta(days=3)))
        dq = (Product
            .delete()
            .where(Product.crawlid.in_(old_crawlers)))
        dq.execute()

        Crawl.delete().where(Crawl.finished==False)

        while True:
            try:
                parser.start()
                break
            except Exception as e:
                print(f'Error occurred while scraping: {e}')
                time.sleep(5)
            time.sleep(60)
        
        time.sleep(60*60)


if __name__ == '__main__':
    while True:
        parser = Parser()
        try: run_spider()
        except Exception as e: print(f'Unexpected exception occurred {e}')
        time.sleep(5)
