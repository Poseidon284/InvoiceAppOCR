# InvoiceAppOCR

InvoiceAppOCR is a Flask application for parsing India Specific PDF invoices,
extracting structured data using OCR and checking compliance using GenAI to 
storing results in a PostgreSQL database for downstream applications.

## Installation

Install dependencies using pip:

``` bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

``` env
POSTGRES_DB_URI=postgresql://<username>:<password>@<rds_endpoint>:<port>/<database_name>
GOOGLE_API_KEY=your_google_api_key
```

## Usage

Create the uploads folder if it does not exist:

``` bash
mkdir uploads
```

Run the application:

``` bash
python app.py
```

Open in your browser:

    http://127.0.0.1:5000/

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss changes.

## License

MIT
