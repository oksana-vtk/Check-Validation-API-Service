
# Check Validation API Service

This project is a backend component of a chatbot built on Corezoid for validating fiscal receipts (checks).
The chatbot allows users to scan a QR code from a receipt, and then sends the extracted URL to this
Flask-based Check Validation API Service for further processing.

## The API performs the following tasks:

- Validates the URL format and extracts the receipt identifier.
- Sends a request to the official tax authority's website to retrieve the receipt.
- If the receipt is found, scrapes and parses the HTML page to extract relevant receipt details.
- Returns the extracted data in a structured JSON format data (such as company name, fiscal code, total amount, etc.)
for further processing by the chatbot.


## Features

- Validates the URL format and extracts the receipt identifier.
- Sends a request to the official tax authority's website to retrieve the receipt.
- If the receipt is found, scrapes and parses the HTML page to extract relevant receipt details.
- Returns the extracted data in a structured JSON format data (such as company name, fiscal code, total amount, etc.)
for further processing by the chatbot.
- Utilizes the `httpx` library for primary web scraping. 
- If standard scraping fails (due to bot protection or rate limits), the API can optionally use the paid `Scrapfly` service for reliable data extraction.
- Utilizes the `BeautifulSoup` library for parsing data.
- Provides descriptive error messages with status codes.
- Supports environment configuration via `.env` file.
- Logs all API calls and errors for debugging.

## Technologies

- Python 3.8+
- Flask
- httpx
- BeautifulSoup (bs4)
- dotenv
- Scrapfly (optional paid service)



