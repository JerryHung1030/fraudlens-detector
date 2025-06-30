from data_download_manager import DataDownloadManager
from data_extraction_manager import DataExtractionManager

LINE_DB_PATH = "./src/blacklist_analysis/data/database/lineid_database.xlsx"
URL_GOOD_DB_PATH = "./src/blacklist_analysis/data/database/url_good_database_new.xlsx"
URL_BAD_DB_PATH = "./src/blacklist_analysis/data/database/url_bad_database.xlsx"


LINE_OPENDATA_PATH = "./src/blacklist_analysis/data/raw_data/line_opendata.csv"
URL_OPENDATA_PATH = "./src/blacklist_analysis/data/raw_data/url_opendata.json"

if __name__ == "__main__":
    data_download_manager = DataDownloadManager()
    data_extraction_manager = DataExtractionManager()
    
    # download blacklist
    file_sources = [
        {"source_type": "file", "file_type": "csv", "col_names": ["帳號"], "file_path": LINE_OPENDATA_PATH, "db_path": LINE_DB_PATH, "url": "https://data.moi.gov.tw/MoiOD/System/DownloadFile.aspx?DATA=7F6BE616-8CE6-449E-8620-5F627C22AA0D"},
        {"source_type": "file", "file_type": "json", "col_names": ["偽冒網址", "接獲通報日期"], "file_path": URL_OPENDATA_PATH, "db_path": URL_BAD_DB_PATH, "url": "https://www-api.moda.gov.tw/OpenData/Files/16352"},
    ]
    data_download_manager.download_blacklist(file_sources)
    
    # # extract data information
    # db_files = [
    #     {"filename": URL_GOOD_DB_PATH, "good_bad": 1},
    #     {"filename": URL_BAD_DB_PATH, "good_bad": 0}
    # ]
    # output_file = "./src/data/database/all_url_good_and_bad.xlsx"
    # data_extraction_manager.get_info_from_file(db_files, output_file)
