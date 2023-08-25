from selenium.webdriver.common.by import By
import re
import pandas as pd
import config.config as config
import jobs_importer
import job_scraper
import config.database as database
from apscheduler.schedulers.blocking import BlockingScheduler

'''
Url 1 : https://www.linkedin.com/jobs/search?keywords=Netflix&location=&geoId=&f_TPR=r604800&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0

f_TPR for past 1 week results - can be hardcoded
f_C - for company - needs to be DYNAMIC 
Filtered Url 1 = https://www.linkedin.com/jobs/search?keywords=&location=&geoId=&position=1&pageNum=0&f_C=165158&f_TPR=r604800

Enhanced Url 1 = https://www.linkedin.com/jobs/search?position=1&pageNum=0&f_C=165158&f_TPR=r604800&geoId=92000000
in jobs page of each company, theres a See All Jobs where we can find f_c (company_id)from where we can search
for apis directly in filtered url 1

geoId=92000000 for WORLDWIDE
by default USA

'''
companies = ['netflix', 'warner-bros--entertainment', 'marvel-studios']


def main():
    try:
        database_conn = config.create_connection()
        if database_conn is not None:
            driver = config.setup_driver()
            session = config.setup_requests()
            total_jobs = list()
            url = 'https://www.linkedin.com/company'
            for company in companies:
                try:
                    print(
                        f'Fetching Total Job Postings of : {company.capitalize()}')
                    driver.get(f'{url}/{company}/')

                    modal_close_button = driver.find_element(
                        "xpath", "//button[@aria-label='Dismiss']")
                    if modal_close_button:
                        driver.execute_script(
                            "arguments[0].click();", modal_close_button)
                    company_tag = driver.find_element(
                        By.CLASS_NAME, "top-card-layout__cta").get_attribute('href')
                    match = re.search(r'f_C=(\d+)', company_tag)
                    if company_tag:
                        if match:
                            f_c_value = match.group(1)
                            jobids = jobs_importer.import_jobs(
                                f_c_value, session)
                            if len(jobids) > 0:
                                total_jobs.append(jobids)
                    else:
                        print('No See Jobs Element')
                except:
                    print(f'No jobs for {company}')
            if len(total_jobs) > 0:
                jobs = [
                    element for inner_array in total_jobs for element in inner_array]
                cursor = database_conn.cursor()
                posts = database.fetch_posts(cursor)
                results = [job for job in jobs if job not in posts]
                if len(results) == 0:
                    print('No jobs to scrape')
                    return
                job_details = job_scraper.fetch_job_infos(results, session)

                # inserting imported jobs in post table
                database.insert_jobs(cursor, job_details)
                # df = pd.DataFrame(job_details)
                # df.index = df.index + 1

                # df.to_csv(f'linkedin_jobs.csv', encoding='utf-8')
                # print(len(job_details), ' jobs imported.')
                # database_conn.commit()

                cursor.close()
                database_conn.close()
    except:
        print('Error Occured.')
        return None


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(main, 'interval', minutes=5)  # Schedule every 5 minutes
    scheduler.start()
