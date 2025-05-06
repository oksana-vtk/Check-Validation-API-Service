# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import traceback
from scrapfly import ScrapeConfig, ScrapflyClient
import asyncio
from dotenv import load_dotenv
import os


# Завантажуємо .env файл
load_dotenv()

# Отримуємо змінні з .env файлу
DOMAIN = os.getenv("DOMAIN")
PATTERN_1 = os.getenv("PATTERN_1")
PATTERN_2 = os.getenv("PATTERN_2")
FISCAL_PREFIX = os.getenv("FISCAL_PREFIX")
REGISTRATION_PREFIX = os.getenv("REGISTRATION_PREFIX")
DATE_PREFIX = os.getenv("DATE_PREFIX")
TIME_PREFIX = os.getenv("TIME_PREFIX")
KEY = os.getenv("SCRAPFLY_KEY")


# API
app = Flask(__name__)


# API_1 Документація в файлі API_DOC.md   /validator/check-info
@app.route("/check-info", methods=["POST"])
def check_info():

    user_data = request.get_json()
    user_url = user_data["url"]
    contact_id = user_data["contact_id"]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open("check_info.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"\n\n {current_datetime} Check_info log\n Contact_id: {contact_id}\n User_url: {user_url}\n")

    # Компіляція регулярних виразів
    regex_1 = re.compile(PATTERN_1)
    regex_2 = re.compile(PATTERN_2)

    # Check the url
    if re.search(regex_1, user_url):

        check_id = re.split(regex_1, user_url)[4]

        correct_url = DOMAIN + check_id

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    elif re.search(regex_2, user_url):

        check_registration_number = re.split(regex_2, user_url)[4]
        check_sum = re.split(regex_2, user_url)[5]
        check_number = re.split(regex_2, user_url)[6]
        check_date = re.split(regex_2, user_url)[7]

        check_id = f"{check_registration_number}/{check_sum}/{check_number}/{check_date}"

        correct_url = DOMAIN + check_id

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    else:

        result_error = {"contact_id": contact_id,
                        "url": user_url,
                        "status": {"code": 4001,
                                   "message": "Other type of url that doesn't satisfy the pattern. "
                                              "Please check the url manually."}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n{current_datetime}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 400

    # Visit the URL
    try:
        response = httpx.get(correct_url, headers=HEADERS, timeout=30.0)
        response.raise_for_status()  # This raises an error if the status is not 200-OK

        soup = BeautifulSoup(response.content, 'html.parser')

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Response status_code: {response.status_code}\n")

        # Find <form> tag
        form_tag = soup.find('form')

        # Check the <form> tag and its content
        if form_tag is None:
            result_error = {"contact_id": contact_id,
                            "url": correct_url,
                            "status": {"code": 4002,
                                       "message": "Tag <form> doesn't found in the response. "
                                                  "Url is incorrect or check is invalid."}}

            with open("check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        # один з варіантів виникнення цієї ситуації - чек справжній є, але він ще не відобразився на сайті,
        # тому інформація по ньому поки що недоступна для скраппінгу.
        # Тоді беремо інформацію з url для чеків зі слешами (pattern_2)
        if form_tag.find('div', class_='grid grid-cols-1 md:grid-cols-3 '
                                       'lg:grid-cols-3 rounded-lg bg-white shadow sm:mt-4 py-5') is None:

            if re.search(regex_1, user_url):

                result_error = {"contact_id": contact_id,
                                "url": correct_url,
                                "check_id": check_id,
                                "status": {"code": 4003,
                                           "message": "Requested info in tag <form> doesn't found. "
                                                      "Check is invalid or doesn't exist."}}

                with open("check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

            elif re.search(regex_2, user_url):

                check_registration_number = re.split(regex_2, user_url)[4]
                check_sum = re.split(regex_2, user_url)[5]
                check_number = re.split(regex_2, user_url)[6]
                check_date = re.split(regex_2, user_url)[7]

                result_error = {# "company_name": company_name,
                                # "fiscal_code": fiscal_code,
                                # "address": address,
                                "registration_number": check_registration_number,
                                # "items_info": items_info,
                                "total_value": float(check_sum),
                                # "payment_type": payment_type,
                                # "payment_type_value": payment_value,
                                "date": check_date,
                                # "time": check_time,
                                # "check_fiscal_number": check_fiscal_number,
                                "factory_number": 'undef_cashreg',
                                "url": correct_url,
                                "check_id": check_id,
                                "check_number": check_number,
                                "contact_id": contact_id,
                                "status": {"code": 4008,
                                           "message": "Info from this check has not yet appeared on the website. "
                                                      "Please try again later."}}

                with open("check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

        # Find div tags from <form> tag
        div_tags = form_tag.find_all('div', class_=["items-center"])

        # Extract company information
        company_name = div_tags[0].text.strip()

        # Extract fiscal code
        fiscal_code = div_tags[1].text.strip().replace(FISCAL_PREFIX, '')

        # Extract address
        address = div_tags[2].text.strip()

        # Extract registration number
        registration_number = div_tags[3].text.strip().replace(REGISTRATION_PREFIX, '')

        # Find dots divider
        dots_divider = div_tags[4].text.strip()

        dots_index = []
        for i in range(len(div_tags)):
            if div_tags[i].text.strip() == dots_divider:
                dots_index.append(i)

        # якщо оплата картою, то розділювачів в чеку було 6 шт
        if len(dots_index) == 6:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            # payment_type_index = dots_index[3] + 1

            payment_index_start = dots_index[3] + 1
            payment_index_end = dots_index[4] - 1

            receipt_info_index_start = dots_index[4] + 1
            receipt_info_index_end = dots_index[5] - 1

            check_number_index = dots_index[5] + 1  # NEW

            # items here

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            # payment_type_tag = div_tags[payment_type_index]
            # payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            # payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")
            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і була решта, то розділювачів в чеку було 7 шт
        elif len(dots_index) == 7:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            receipt_info_index_start = dots_index[5] + 1
            receipt_info_index_end = dots_index[6] - 1

            check_number_index = dots_index[6] + 1  # NEW

            # items here

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і картою, і була решта, то розділювачів в чеку було 8 шт
        elif len(dots_index) == 8:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            # something here

            receipt_info_index_start = dots_index[6] + 1
            receipt_info_index_end = dots_index[7] - 1

            check_number_index = dots_index[7] + 1  # NEW

            # items here

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # інша кількість розділювачів
        else:

            result_error = {"company_name": company_name,
                            "fiscal_code": fiscal_code,
                            "address": address,
                            "registration_number": registration_number,
                            "url": correct_url,
                            "check_id": check_id,
                            "contact_id": contact_id,
                            "status": {"code": 4004,
                                       "message": "Another type of check: another number of dots_divider!"}}

            with open("check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_json:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        result_json = {"company_name": company_name,
                       "fiscal_code": fiscal_code,
                       "address": address,
                       "registration_number": registration_number,
                       "total_value": total_value,
                       # "payment_type": payment_type,
                       # "payment_type_value": payment_value,
                       "date": check_date,
                       "time": check_time,
                       "check_fiscal_number": check_fiscal_number,
                       "factory_number": factory_number,
                       "url": correct_url,
                       "check_id": check_id,
                       "check_number": check_number,
                       "contact_id": contact_id,
                       "status": {"code": 200,
                                  "message": "Check_info process was successful."}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_json:\n{json.dumps(result_json, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_json)

    # якщо скраппінг неуспішний

    # Handles timeout-specific issues
    except httpx.ConnectTimeout:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4005,
                                   "message": "Connection timeout. Scraping failed!"}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 408

    # Handles HTTP status errors (e.g., 404 Not Found, 500 Server Error)
    except httpx.HTTPStatusError as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url,
                              "contact_id": contact_id,
                              "code": e.response.status_code,
                              "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4006,
                                   "message": "HTTP error occurred: " + str(e)}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), e.response.status_code

    # Catches any unexpected errors and logs the traceback for easier debugging
    except Exception as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4007,
                                   "message": "An unexpected error occurred during scraping."}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 500


# API_2 Документація в файлі API_DOC.md   /validator/check-full-info
@app.route("/check-full-info", methods=["POST"])
def check_full_info():

    user_data = request.get_json()
    user_url = user_data["url"]
    contact_id = user_data["contact_id"]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open("check_info.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"\n\n {current_datetime} Check_info log\n Contact_id: {contact_id}\n User_url: {user_url}\n")

    # Компіляція регулярних виразів
    regex_1 = re.compile(PATTERN_1)
    regex_2 = re.compile(PATTERN_2)

    if re.search(regex_1, user_url):

        check_id = re.split(regex_1, user_url)[4]

        correct_url = DOMAIN + check_id

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    elif re.search(regex_2, user_url):

        check_registration_number = re.split(regex_2, user_url)[4]
        check_sum = re.split(regex_2, user_url)[5]
        check_number = re.split(regex_2, user_url)[6]
        check_date = re.split(regex_2, user_url)[7]

        check_id = f"{check_registration_number}/{check_sum}/{check_number}/{check_date}"

        correct_url = DOMAIN + check_id

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    else:

        result_error = {"contact_id": contact_id,
                        "url": user_url,
                        "status": {"code": 4001,
                                   "message": "Other type of url that doesn't satisfy the pattern. "
                                              "Please check the url manually."}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n{current_datetime}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 400

    # Visit the URL
    try:
        response = httpx.get(correct_url, headers=HEADERS, timeout=30.0)
        response.raise_for_status()  # This raises an error if the status is not 200-OK

        soup = BeautifulSoup(response.content, 'html.parser')

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Response status_code: {response.status_code}\n")

        # Find <form> tag
        form_tag = soup.find('form')

        # Check the <form> tag and its content
        if form_tag is None:
            result_error = {"contact_id": contact_id,
                            "url": correct_url,
                            "status": {"code": 4002,
                                       "message": "Tag <form> doesn't found in the response. "
                                                  "Url is incorrect or check is invalid."}}

            with open("check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        # один з варіантів виникнення цієї ситуації - чек справжній є, але він ще не відобразився на сайті,
        # тому інформація по ньому поки що недоступна для скраппінгу.
        # Тоді беремо інформацію з url для чеків зі слешами (pattern_2)
        if form_tag.find('div', class_='grid grid-cols-1 md:grid-cols-3 '
                                       'lg:grid-cols-3 rounded-lg bg-white shadow sm:mt-4 py-5') is None:

            if re.search(regex_1, user_url):

                result_error = {"contact_id": contact_id,
                                "url": correct_url,
                                "check_id": check_id,
                                "status": {"code": 4003,
                                           "message": "Requested info in tag <form> doesn't found. "
                                                      "Check is invalid or doesn't exist."}}

                with open("check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

            elif re.search(regex_2, user_url):

                check_registration_number = re.split(regex_2, user_url)[4]
                check_sum = re.split(regex_2, user_url)[5]
                check_number = re.split(regex_2, user_url)[6]
                check_date = re.split(regex_2, user_url)[7]

                result_error = {# "company_name": company_name,
                                # "fiscal_code": fiscal_code,
                                # "address": address,
                                "registration_number": check_registration_number,
                                # "items_info": items_info,
                                "total_value": float(check_sum),
                                # "payment_type": payment_type,
                                # "payment_type_value": payment_value,
                                "date": check_date,
                                # "time": check_time,
                                # "check_fiscal_number": check_fiscal_number,
                                "factory_number": 'undef_cashreg',
                                "url": correct_url,
                                "check_id": check_id,
                                "check_number": check_number,
                                "contact_id": contact_id,
                                "status": {"code": 4008,
                                           "message": "Info from this check has not yet appeared on the website. "
                                                      "Please try again later."}}

                with open("check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

        # Find div tags from <form> tag
        div_tags = form_tag.find_all('div', class_=["items-center"])

        # Extract company information
        company_name = div_tags[0].text.strip()

        # Extract fiscal code
        fiscal_code = div_tags[1].text.strip().replace(FISCAL_PREFIX, '')

        # Extract address
        address = div_tags[2].text.strip()

        # Extract registration number
        registration_number = div_tags[3].text.strip().replace(REGISTRATION_PREFIX, '')

        # Find dots divider
        dots_divider = div_tags[4].text.strip()

        dots_index = []
        for i in range(len(div_tags)):
            if div_tags[i].text.strip() == dots_divider:
                dots_index.append(i)

        # якщо оплата картою, то розділювачів в чеку було 6 шт
        if len(dots_index) == 6:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            # payment_type_index = dots_index[3] + 1

            payment_index_start = dots_index[3] + 1
            payment_index_end = dots_index[4] - 1

            receipt_info_index_start = dots_index[4] + 1
            receipt_info_index_end = dots_index[5] - 1

            check_number_index = dots_index[5] + 1  # NEW

            # items
            items = []
            for i in range(items_index_start, items_index_end + 1):
                items.append(div_tags[i])

            # Extract items
            items_info = []
            for i in range(0, len(items), 2):
                # Get product name and quantity/price details from the first div
                product_info = items[i].find_all('span')
                product_name = product_info[0].text.strip()
                quantity_price = product_info[1].text.strip()
                quantity = round(float(quantity_price.split(' x ')[0]), 2)
                price = round(float(quantity_price.split(' x ')[1]), 2)

                # Get total price from the next div
                price_pattern = r"^(.*\d)(\s.*)"
                total_price_info = items[i + 1].find_all('span')
                # total_price = round(float(total_price_info[1].text.strip().replace(' B', '').replace(' A', '').replace(' D', '')), 2)
                total_price = round(float(re.split(price_pattern, total_price_info[1].text.strip())[1]), 2)

                # Add parsed data to the list
                items_info.append({"product_name": product_name,
                                   "quantity_price": quantity_price,
                                   "quantity": quantity,
                                   "price": price,
                                   "total_price": total_price})

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            # payment_type_tag = div_tags[payment_type_index]
            # payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            # payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")
            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і була решта, то розділювачів в чеку було 7 шт
        elif len(dots_index) == 7:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            receipt_info_index_start = dots_index[5] + 1
            receipt_info_index_end = dots_index[6] - 1

            check_number_index = dots_index[6] + 1  # NEW

            # items
            items = []
            for i in range(items_index_start, items_index_end + 1):
                items.append(div_tags[i])

            # Extract items
            items_info = []
            for i in range(0, len(items), 2):
                # Get product name and quantity/price details from the first div
                product_info = items[i].find_all('span')
                product_name = product_info[0].text.strip()
                quantity_price = product_info[1].text.strip()
                quantity = round(float(quantity_price.split(' x ')[0]), 2)
                price = round(float(quantity_price.split(' x ')[1]), 2)

                # Get total price from the next div
                price_pattern = r"^(.*\d)(\s.*)"
                total_price_info = items[i + 1].find_all('span')
                # total_price = round(float(total_price_info[1].text.strip().replace(' B', '').replace(' A', '').replace(' D', '')), 2)
                total_price = round(float(re.split(price_pattern, total_price_info[1].text.strip())[1]), 2)

                # Add parsed data to the list
                items_info.append({"product_name": product_name,
                                   "quantity_price": quantity_price,
                                   "quantity": quantity,
                                   "price": price,
                                   "total_price": total_price})

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і картою, і була решта, то розділювачів в чеку було 8 шт
        elif len(dots_index) == 8:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            # something here

            receipt_info_index_start = dots_index[6] + 1
            receipt_info_index_end = dots_index[7] - 1

            check_number_index = dots_index[7] + 1  # NEW

            # items
            items = []
            for i in range(items_index_start, items_index_end + 1):
                items.append(div_tags[i])

            # Extract items
            items_info = []
            for i in range(0, len(items), 2):
                # Get product name and quantity/price details from the first div
                product_info = items[i].find_all('span')
                product_name = product_info[0].text.strip()
                quantity_price = product_info[1].text.strip()
                quantity = round(float(quantity_price.split(' x ')[0]), 2)
                price = round(float(quantity_price.split(' x ')[1]), 2)

                # Get total price from the next div
                price_pattern = r"^(.*\d)(\s.*)"
                total_price_info = items[i + 1].find_all('span')
                # total_price = round(float(total_price_info[1].text.strip().replace(' B', '').replace(' A', '').replace(' D', '')), 2)
                total_price = round(float(re.split(price_pattern, total_price_info[1].text.strip())[1]), 2)

                # Add parsed data to the list
                items_info.append({"product_name": product_name,
                                   "quantity_price": quantity_price,
                                   "quantity": quantity,
                                   "price": price,
                                   "total_price": total_price})

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # інша кількість розділювачів
        else:

            result_error = {"company_name": company_name,
                            "fiscal_code": fiscal_code,
                            "address": address,
                            "registration_number": registration_number,
                            "url": correct_url,
                            "check_id": check_id,
                            "contact_id": contact_id,
                            "status": {"code": 4004,
                                       "message": "Another type of check: another number of dots_divider!"}}

            with open("check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_json:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        result_json = {"company_name": company_name,
                       "fiscal_code": fiscal_code,
                       "address": address,
                       "registration_number": registration_number,
                       "items_info": items_info,
                       "total_value": total_value,
                       # "payment_type": payment_type,
                       # "payment_type_value": payment_value,
                       "date": check_date,
                       "time": check_time,
                       "check_fiscal_number": check_fiscal_number,
                       "factory_number": factory_number,
                       "url": correct_url,
                       "check_id": check_id,
                       "check_number": check_number,
                       "contact_id": contact_id,
                       "status": {"code": 200,
                                  "message": "Check_full_info process was successful."}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_json:\n{json.dumps(result_json, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_json)

    # якщо скраппінг неуспішний

    # Handles timeout-specific issues
    except httpx.ConnectTimeout:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4005,
                                   "message": "Connection timeout. Scraping failed!"}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 408

    # Handles HTTP status errors (e.g., 404 Not Found, 500 Server Error)
    except httpx.HTTPStatusError as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"contact_id": contact_id,
                              "url": correct_url,
                              "code": e.response.status_code,
                              "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4006,
                                   "message": "HTTP error occurred: " + str(e)}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), e.response.status_code

    # Catches any unexpected errors and logs the traceback for easier debugging
    except Exception as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4007,
                                   "message": "An unexpected error occurred during scraping."}}

        with open("check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 500


# API_3 Документація в файлі API_DOC.md   /validator/check-info-scrapfly
@app.route("/check-info-scrapfly", methods=["POST"])
def check_info_scrapfly():

    user_data = request.get_json()
    user_url = user_data["url"]
    contact_id = user_data["contact_id"]

    SCRAPFLY = ScrapflyClient(key=KEY)

    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"\n\n {current_datetime} Check_info SCRAPFLY log\n Contact_id: {contact_id}\n User_url: {user_url}\n")

    # Компіляція регулярних виразів
    regex_1 = re.compile(PATTERN_1)
    regex_2 = re.compile(PATTERN_2)

    if re.search(regex_1, user_url):

        check_id = re.split(regex_1, user_url)[4]

        correct_url = DOMAIN + check_id

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    elif re.search(regex_2, user_url):

        check_registration_number = re.split(regex_2, user_url)[4]
        check_sum = re.split(regex_2, user_url)[5]
        check_number = re.split(regex_2, user_url)[6]
        check_date = re.split(regex_2, user_url)[7]

        check_id = f"{check_registration_number}/{check_sum}/{check_number}/{check_date}"

        correct_url = DOMAIN + check_id

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    else:

        result_error = {"contact_id": contact_id,
                        "url": user_url,
                        "status": {"code": 4001,
                                   "message": "Other type of url that doesn't satisfy the pattern."
                                              "Please check the url manually."}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n{current_datetime}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 400

    # Visit the URL
    try:

        async def scrape_url(url):
            result = await SCRAPFLY.async_scrape(ScrapeConfig(url, timeout=150000))
            return result

        response = asyncio.run(scrape_url(correct_url))
        # response.raise_for_status  # This raises an error if the status is not 200-OK

        soup = BeautifulSoup(response.content, 'html.parser')

        with open("scrapfly_scrapping_result.log", "a", encoding="utf-8") as scraplog_file:
            scraplog_file.write(f"\n{current_datetime}\n")
            scraplog_file.write(f" Response.content:\n {response.content}\n")

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Response status_code: {response.status_code}\n")

        # Find <form> tag
        form_tag = soup.find('form')

        # Check the <form> tag and its content
        if form_tag is None:
            result_error = {"contact_id": contact_id,
                            "url": user_url,
                            "status": {"code": 4002,
                                       "message": "Tag <form> doesn't found in the response. "
                                                  "Url is incorrect or check is invalid."}}

            with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        # один з варіантів виникнення цієї ситуації - чек справжній є, але він ще не відобразився на сайті,
        # тому інформація по ньому поки що недоступна для скраппінгу.
        # Тоді беремо інформацію з url для чеків зі слешами (pattern_2)
        if form_tag.find('div', class_='grid grid-cols-1 md:grid-cols-3 '
                                   'lg:grid-cols-3 rounded-lg bg-white shadow sm:mt-4 py-5') is None:
            if re.search(regex_1, user_url):

                result_error = {"contact_id": contact_id,
                                "url": correct_url,
                                "check_id": check_id,
                                "status": {"code": 4003,
                                           "message": "Requested info in tag <form> doesn't found. "
                                                      "Check is invalid or doesn't exist."}}

                with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

            elif re.search(regex_2, user_url):

                check_registration_number = re.split(regex_2, user_url)[4]
                check_sum = re.split(regex_2, user_url)[5]
                check_number = re.split(regex_2, user_url)[6]
                check_date = re.split(regex_2, user_url)[7]

                result_error = {# "company_name": company_name,
                                # "fiscal_code": fiscal_code,
                                # "address": address,
                                "registration_number": check_registration_number,
                                # "items_info": items_info,
                                "total_value": float(check_sum),
                                # "payment_type": payment_type,
                                # "payment_type_value": payment_value,
                                "date": check_date,
                                # "time": check_time,
                                # "check_fiscal_number": check_fiscal_number,
                                "factory_number": 'undef_cashreg',
                                "url": correct_url,
                                "check_id": check_id,
                                "check_number": check_number,
                                "contact_id": contact_id,
                                "status": {"code": 4008,
                                           "message": "Info from this check has not yet appeared on the website. "
                                                      "Please try again later."}}

                with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

        # Find div tags from <form> tag
        div_tags = form_tag.find_all('div', class_=["items-center"])

        # Extract company information
        company_name = div_tags[0].text.strip()

        # Extract fiscal code
        fiscal_code = div_tags[1].text.strip().replace(FISCAL_PREFIX, '')

        # Extract address
        address = div_tags[2].text.strip()

        # Extract registration number
        registration_number = div_tags[3].text.strip().replace(REGISTRATION_PREFIX, '')

        # Find dots divider
        dots_divider = div_tags[4].text.strip()

        dots_index = []
        for i in range(len(div_tags)):
            if div_tags[i].text.strip() == dots_divider:
                dots_index.append(i)

        # якщо оплата картою, то розділювачів в чеку було 6 шт
        if len(dots_index) == 6:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            # payment_type_index = dots_index[3] + 1

            payment_index_start = dots_index[3] + 1
            payment_index_end = dots_index[4] - 1

            receipt_info_index_start = dots_index[4] + 1
            receipt_info_index_end = dots_index[5] - 1

            check_number_index = dots_index[5] + 1  # NEW

            # items here

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            # payment_type_tag = div_tags[payment_type_index]
            # payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            # payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")
            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і була решта, то розділювачів в чеку було 7 шт
        elif len(dots_index) == 7:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            receipt_info_index_start = dots_index[5] + 1
            receipt_info_index_end = dots_index[6] - 1

            check_number_index = dots_index[6] + 1  # NEW

            # items here

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                        next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(
                        float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і картою, і була решта, то розділювачів в чеку було 8 шт
        elif len(dots_index) == 8:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            # something here

            receipt_info_index_start = dots_index[6] + 1
            receipt_info_index_end = dots_index[7] - 1

            check_number_index = dots_index[7] + 1  # NEW

            # items here

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                           "total_value": total_info_value})

            total_value = float(
                        next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(
                        float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # інша кількість розділювачів
        else:

            result_error = {"company_name": company_name,
                            "fiscal_code": fiscal_code,
                            "address": address,
                            "registration_number": registration_number,
                            "url": correct_url,
                            "check_id": check_id,
                            "contact_id": contact_id,
                            "status": {"code": 4004,
                                       "message": "Another type of check: another number of dots_divider!"}}

            with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_json:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        result_json = {"company_name": company_name,
                       "fiscal_code": fiscal_code,
                       "address": address,
                       "registration_number": registration_number,
                       "total_value": total_value,
                       # "payment_type": payment_type,
                       # "payment_type_value": payment_value,
                       "date": check_date,
                       "time": check_time,
                       "check_fiscal_number": check_fiscal_number,
                       "factory_number": factory_number,
                       "url": correct_url,
                       "check_id": check_id,
                       "check_number": check_number,
                       "contact_id": contact_id,
                       "status": {"code": 200,
                                  "message": "Check_info process was successful."}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_json:\n{json.dumps(result_json, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_json)

    # якщо скраппінг неуспішний

    # Handles timeout-specific issues
    except httpx.ConnectTimeout:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4005,
                                   "message": "Connection timeout. Scraping failed!"}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 408

    # Handles HTTP status errors (e.g., 404 Not Found, 500 Server Error)
    except httpx.HTTPStatusError as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"contact_id": contact_id,
                              "url": correct_url,
                              "code": e.response.status_code,
                              "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4006,
                                   "message": "HTTP error occurred: " + str(e)}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), e.response.status_code

    # Catches any unexpected errors and logs the traceback for easier debugging
    except Exception as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4007,
                                   "message": "An unexpected error occurred during scraping."}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 500


# API_4 Документація в файлі API_DOC.md   /validator/check-full-info-scrapfly
@app.route("/check-full-info-scrapfly", methods=["POST"])
def check_full_info_scrapfly():

    user_data = request.get_json()
    user_url = user_data["url"]
    contact_id = user_data["contact_id"]

    SCRAPFLY = ScrapflyClient(key=KEY)

    current_datetime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"\n\n {current_datetime} Check_info SCRAPFLY log\n Contact_id: {contact_id}\n User_url: {user_url}\n")

    # Компіляція регулярних виразів
    regex_1 = re.compile(PATTERN_1)
    regex_2 = re.compile(PATTERN_2)

    if re.search(regex_1, user_url):

        check_id = re.split(regex_1, user_url)[4]

        correct_url = DOMAIN + check_id

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    elif re.search(regex_2, user_url):

        check_registration_number = re.split(regex_2, user_url)[4]
        check_sum = re.split(regex_2, user_url)[5]
        check_number = re.split(regex_2, user_url)[6]
        check_date = re.split(regex_2, user_url)[7]

        check_id = f"{check_registration_number}/{check_sum}/{check_number}/{check_date}"

        correct_url = DOMAIN + check_id

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Check_id: {check_id}\n")
            log_file.write(f" Correct_url: {correct_url}\n")

    else:

        result_error = {"contact_id": contact_id,
                        "url": user_url,
                        "status": {"code": 4001,
                                   "message": "Other type of url that doesn't satisfy the pattern."
                                              "Please check the url manually."}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n{current_datetime}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 400

    # Visit the URL
    try:

        async def scrape_url(url):
            result = await SCRAPFLY.async_scrape(ScrapeConfig(url, timeout=150000))
            return result

        response = asyncio.run(scrape_url(correct_url))
        # response.raise_for_status  # This raises an error if the status is not 200-OK

        soup = BeautifulSoup(response.content, 'html.parser')

        with open("scrapfly_scrapping_result.log", "a", encoding="utf-8") as scraplog_file:
            scraplog_file.write(f"\n{current_datetime}\n")
            scraplog_file.write(f" Response.content:\n {response.content}\n")

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Response status_code: {response.status_code}\n")

        # Find <form> tag
        form_tag = soup.find('form')

        # Check the <form> tag and its content
        if form_tag is None:
            result_error = {"contact_id": contact_id,
                            "url": user_url,
                            "status": {"code": 4002,
                                       "message": "Tag <form> doesn't found in the response. "
                                                  "Url is incorrect or check is invalid."}}

            with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        # один з варіантів виникнення цієї ситуації - чек справжній є, але він ще не відобразився на сайті,
        # тому інформація по ньому поки що недоступна для скраппінгу.
        # Тоді беремо інформацію з url для чеків зі слешами (pattern_2)
        if form_tag.find('div', class_='grid grid-cols-1 md:grid-cols-3 '
                                   'lg:grid-cols-3 rounded-lg bg-white shadow sm:mt-4 py-5') is None:
            if re.search(regex_1, user_url):

                result_error = {"contact_id": contact_id,
                                "url": correct_url,
                                "check_id": check_id,
                                "status": {"code": 4003,
                                           "message": "Requested info in tag <form> doesn't found. "
                                                      "Check is invalid or doesn't exist."}}

                with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

            elif re.search(regex_2, user_url):

                check_registration_number = re.split(regex_2, user_url)[4]
                check_sum = re.split(regex_2, user_url)[5]
                check_number = re.split(regex_2, user_url)[6]
                check_date = re.split(regex_2, user_url)[7]

                result_error = {# "company_name": company_name,
                                # "fiscal_code": fiscal_code,
                                # "address": address,
                                "registration_number": check_registration_number,
                                # "items_info": items_info,
                                "total_value": float(check_sum),
                                # "payment_type": payment_type,
                                # "payment_type_value": payment_value,
                                "date": check_date,
                                # "time": check_time,
                                # "check_fiscal_number": check_fiscal_number,
                                "factory_number": 'undef_cashreg',
                                "url": correct_url,
                                "check_id": check_id,
                                "check_number": check_number,
                                "contact_id": contact_id,
                                "status": {"code": 4008,
                                           "message": "Info from this check has not yet appeared on the website. "
                                                      "Please try again later."}}

                with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                    log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                    error_file.write(f"\n{current_datetime}\n")
                    error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

                return jsonify(result_error), 400

        # Find div tags from <form> tag
        div_tags = form_tag.find_all('div', class_=["items-center"])

        # Extract company information
        company_name = div_tags[0].text.strip()

        # Extract fiscal code
        fiscal_code = div_tags[1].text.strip().replace(FISCAL_PREFIX, '')

        # Extract address
        address = div_tags[2].text.strip()

        # Extract registration number
        registration_number = div_tags[3].text.strip().replace(REGISTRATION_PREFIX, '')

        # Find dots divider
        dots_divider = div_tags[4].text.strip()

        dots_index = []
        for i in range(len(div_tags)):
            if div_tags[i].text.strip() == dots_divider:
                dots_index.append(i)

        # якщо оплата картою, то розділювачів в чеку було 6 шт
        if len(dots_index) == 6:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            # payment_type_index = dots_index[3] + 1

            payment_index_start = dots_index[3] + 1
            payment_index_end = dots_index[4] - 1

            receipt_info_index_start = dots_index[4] + 1
            receipt_info_index_end = dots_index[5] - 1

            check_number_index = dots_index[5] + 1  # NEW

            # items here
            items = []
            for i in range(items_index_start, items_index_end + 1):
                items.append(div_tags[i])

            # Extract items
            items_info = []
            for i in range(0, len(items), 2):
                # Get product name and quantity/price details from the first div
                product_info = items[i].find_all('span')
                product_name = product_info[0].text.strip()
                quantity_price = product_info[1].text.strip()
                quantity = round(float(quantity_price.split(' x ')[0]), 2)
                price = round(float(quantity_price.split(' x ')[1]), 2)

                # Get total price from the next div
                price_pattern = r"^(.*\d)(\s.*)"
                total_price_info = items[i + 1].find_all('span')
                total_price = round(float(re.split(price_pattern, total_price_info[1].text.strip())[1]), 2)

                # Add parsed data to the list
                items_info.append({"product_name": product_name,
                                   "quantity_price": quantity_price,
                                   "quantity": quantity,
                                   "price": price,
                                   "total_price": total_price})

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            # payment_type_tag = div_tags[payment_type_index]
            # payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            # payment_value = round(float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")
            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і була решта, то розділювачів в чеку було 7 шт
        elif len(dots_index) == 7:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            receipt_info_index_start = dots_index[5] + 1
            receipt_info_index_end = dots_index[6] - 1

            check_number_index = dots_index[6] + 1  # NEW

            # items here
            items = []
            for i in range(items_index_start, items_index_end + 1):
                items.append(div_tags[i])

            # Extract items
            items_info = []
            for i in range(0, len(items), 2):
                # Get product name and quantity/price details from the first div
                product_info = items[i].find_all('span')
                product_name = product_info[0].text.strip()
                quantity_price = product_info[1].text.strip()
                quantity = round(float(quantity_price.split(' x ')[0]), 2)
                price = round(float(quantity_price.split(' x ')[1]), 2)

                # Get total price from the next div
                price_pattern = r"^(.*\d)(\s.*)"
                total_price_info = items[i + 1].find_all('span')
                total_price = round(float(re.split(price_pattern, total_price_info[1].text.strip())[1]), 2)

                # Add parsed data to the list
                items_info.append({"product_name": product_name,
                                   "quantity_price": quantity_price,
                                   "quantity": quantity,
                                   "price": price,
                                   "total_price": total_price})

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                        next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(
                        float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # якщо оплата готівкою і картою, і була решта, то розділювачів в чеку було 8 шт
        elif len(dots_index) == 8:

            # Find indexes for needed information

            items_index_start = dots_index[0] + 1
            items_index_end = dots_index[1] - 1

            total_index_start = dots_index[1] + 1
            total_index_end = dots_index[2] - 1

            taxes_index_start = dots_index[2] + 1
            taxes_index_end = dots_index[3] - 1

            payment_type_index = dots_index[3] + 1

            cashrest_index = dots_index[4] + 1

            # something here

            receipt_info_index_start = dots_index[6] + 1
            receipt_info_index_end = dots_index[7] - 1

            check_number_index = dots_index[7] + 1  # NEW

            # items here
            items = []
            for i in range(items_index_start, items_index_end + 1):
                items.append(div_tags[i])

            # Extract items
            items_info = []
            for i in range(0, len(items), 2):
                # Get product name and quantity/price details from the first div
                product_info = items[i].find_all('span')
                product_name = product_info[0].text.strip()
                quantity_price = product_info[1].text.strip()
                quantity = round(float(quantity_price.split(' x ')[0]), 2)
                price = round(float(quantity_price.split(' x ')[1]), 2)

                # Get total price from the next div
                price_pattern = r"^(.*\d)(\s.*)"
                total_price_info = items[i + 1].find_all('span')
                total_price = round(float(re.split(price_pattern, total_price_info[1].text.strip())[1]), 2)

                # Add parsed data to the list
                items_info.append({"product_name": product_name,
                                   "quantity_price": quantity_price,
                                   "quantity": quantity,
                                   "price": price,
                                   "total_price": total_price})

            # total
            # total = div_tags[total_index]
            # label = total.find_all('span')[0].text.strip()
            # total_value = round(float(total.find_all('span')[1].text.strip()), 2)

            # total
            total = []
            for i in range(total_index_start, total_index_end + 1):
                total.append(div_tags[i])

            # Extract total
            total_info = []
            for i in range(0, len(total)):
                # Get the label (e.g., TOTAL, SUBTOTAL)
                total_info_label = total[i].find('span', class_='text-base').get_text(strip=True)
                total_info_value = total[i].find('span', class_='text-base font-medium').get_text(strip=True)

                total_info.append({"total_label": total_info_label,
                                   "total_value": total_info_value})

            total_value = float(
                        next((item['total_value'] for item in total_info if item['total_label'] == 'TOTAL'), None))

            # taxes
            taxes = []
            for i in range(taxes_index_start, taxes_index_end + 1):
                taxes.append(div_tags[i])

            # payment_type
            payment_type_tag = div_tags[payment_type_index]

            payment_type = payment_type_tag.find('span', class_='text-base').text.strip()
            payment_value = round(
                        float(payment_type_tag.find('span', class_='text-base font-medium').text.strip()), 2)

            cashrest_tag = div_tags[cashrest_index]
            cashrest_type = cashrest_tag.find('span', class_='text-base').text.strip()
            cashrest_value = cashrest_tag.find('span', class_='text-base font-medium').text.strip()

            # receipt_info
            receipt_info = []
            for i in range(receipt_info_index_start, receipt_info_index_end + 1):
                receipt_info.append(div_tags[i])

            # Extract check date and time
            date_time_div = receipt_info[0]

            date_info = date_time_div.find_all('span')[0].text.replace(DATE_PREFIX, '')
            date_object = datetime.strptime(date_info, "%d.%m.%Y")
            check_date = date_object.strftime("%d-%m-%Y")

            check_time = date_time_div.find_all('span')[1].text.replace(TIME_PREFIX, '').strip()

            # Extract fiscal number
            fiscal_div = receipt_info[1]
            check_fiscal_number = fiscal_div.find_all('span')[1].text.strip().split(':')[1].strip()

            # Extract factory number
            factory_div = receipt_info[2]
            factory_number = factory_div.find_all('span')[1].text.strip()

            # Extract check_number
            check_number_tag = div_tags[check_number_index]
            check_number = check_number_tag.find('span', class_='text-base font-medium').get_text(strip=True)

        # інша кількість розділювачів
        else:

            result_error = {"company_name": company_name,
                            "fiscal_code": fiscal_code,
                            "address": address,
                            "registration_number": registration_number,
                            "url": correct_url,
                            "check_id": check_id,
                            "contact_id": contact_id,
                            "status": {"code": 4004,
                                       "message": "Another type of check: another number of dots_divider!"}}

            with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
                log_file.write(f" Result_json:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
                error_file.write(f"\n{current_datetime}\n")
                error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

            return jsonify(result_error), 400

        result_json = {"company_name": company_name,
                       "fiscal_code": fiscal_code,
                       "address": address,
                       "registration_number": registration_number,
                       "total_value": total_value,
                       # "payment_type": payment_type,
                       # "payment_type_value": payment_value,
                       "date": check_date,
                       "time": check_time,
                       "check_fiscal_number": check_fiscal_number,
                       "factory_number": factory_number,
                       "url": correct_url,
                       "check_id": check_id,
                       "check_number": check_number,
                       "contact_id": contact_id,
                       "status": {"code": 200,
                                  "message": "Check_info process was successful."}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Result_json:\n{json.dumps(result_json, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_json)

    # якщо скраппінг неуспішний

    # Handles timeout-specific issues
    except httpx.ConnectTimeout:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4005,
                                   "message": "Connection timeout. Scraping failed!"}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 408

    # Handles HTTP status errors (e.g., 404 Not Found, 500 Server Error)
    except httpx.HTTPStatusError as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"contact_id": contact_id,
                              "url": correct_url,
                              "code": e.response.status_code,
                              "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4006,
                                   "message": "HTTP error occurred: " + str(e)}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), e.response.status_code

    # Catches any unexpected errors and logs the traceback for easier debugging
    except Exception as e:

        error_in_scrapping = "".join(traceback.format_exc()).strip()
        print(error_in_scrapping)

        data_for_error_log = {"url": correct_url, "contact_id": contact_id, "error": error_in_scrapping}

        result_error = {"contact_id": contact_id,
                        "url": correct_url,
                        "status": {"code": 4007,
                                   "message": "An unexpected error occurred during scraping."}}

        with open("scrapfly_check_info.log", "a", encoding="utf-8") as log_file:
            log_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            log_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        with open("scrapfly_check_error.log", "a", encoding="utf-8") as error_file:
            error_file.write(f"\n {current_datetime}\n")
            error_file.write(f" Error in scrapping: \n{json.dumps(data_for_error_log, ensure_ascii=False)}\n")
            error_file.write(f" Result_error:\n{json.dumps(result_error, ensure_ascii=False, indent=4)}\n")

        return jsonify(result_error), 500


if __name__ == "__main__":
    app.run(debug=True)
