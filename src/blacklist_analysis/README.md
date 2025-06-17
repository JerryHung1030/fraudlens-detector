# URL Blacklist Analysis

1. data_download_manager.py
    - Download open data from source, and save the necessary columns into a .xlsx database file.
2. data_extraction_manager.py
    - Get url whois info and process them then save into a good/bad url combined file.
3. feature_analysis_manager.py
    - Run tests to choose what columns to put into model.
4. algo_analysis_manager.py
    - Run tests to choose which model to use
5. model_generate_manager.py
    - Run the chosen model and save result for future use.