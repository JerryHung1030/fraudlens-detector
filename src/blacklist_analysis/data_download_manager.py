import requests
import json
import os
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime


class DataDownloadManager:
    def __init__(self):
        pass
        
    def download_blacklist(self, source_list):
        if source_list is None or len(source_list) == 0:
            return 
        for source in source_list:
            if source["source_type"] == "api":
                self._download_and_process_api(source)
            elif source["source_type"] == "file":
                if source["file_type"] == "csv":
                    self._download_and_process_csv(source)
                elif source["file_type"] == "json":
                    self._download_and_process_json(source)
                    
    def _download_and_process_api(self, source):
        pass
    
    def _download_and_process_json(self, source):
        response = requests.get(source["url"])
        if response.status_code == 200:
            data = response.json()
            os.makedirs(os.path.dirname(source["file_path"]), exist_ok=True)
            with open(source["file_path"], "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self._update_db_from_json(source["file_path"], source["db_path"], source["col_names"], source["url"])
        else:
            print("Failed:", source["url"], response.status_code)
    
    def _download_and_process_csv(self, source):
        response = requests.get(source["url"])
        if response.status_code == 200:
            with open(source["file_path"], "wb") as f:
                f.write(response.content)
            self._update_db_from_csv(source["file_path"], source["db_path"], source["col_names"], source["url"])
        else:
            print("Failed:", source["url"], response.status_code)
            
    def _update_db_from_csv(self, filepath, db_path, col_names, source_url):
        df_data = pd.read_csv(filepath, encoding="utf-8")
        df_selected = df_data[col_names].dropna(how="any")
        self._append_to_db(df_selected, col_names, filepath, db_path, source_url)

    def _update_db_from_json(self, filepath, db_path, col_names, source_url):
        with open(filepath, "r", encoding="utf-8") as f:
            all_data = json.load(f)
        df_selected = pd.DataFrame(all_data)[col_names].dropna(how="any")
        self._append_to_db(df_selected, col_names, filepath, db_path, source_url)  
        
    def _append_to_db(self, df, col_names, filepath, db_path, source_url):
        is_lineid = "line" in filepath.lower()
        today = datetime.now().strftime("%Y-%m-%d")

        new_rows = []
        if is_lineid:
            for _, row in df.iterrows():
                new_rows.append({
                    "id": row[col_names[0]],
                    "Download Date": today,
                    "Source": source_url
                })
        else:
            if len(col_names) == 2:
                for _, row in df.iterrows():
                    url = row[col_names[0]]
                    parsed_url = urlparse(url)
                    domain = (parsed_url.hostname or url).lower().strip()
                    new_rows.append({
                        "url": domain,
                        "Found Date": row[col_names[1]],
                        "Download Date": today,
                        "Source": source_url
                    })

            else:
                for _, row in df.iterrows():
                    new_rows.append({
                        "url": row[col_names[0]],
                        "Found Date": None,
                        "Download Date": today,
                        "Source": source_url
                    })
        new_df = pd.DataFrame(new_rows)
        
        if os.path.exists(db_path):
            old_df = pd.read_excel(db_path)
            new_df = pd.concat([old_df, new_df], ignore_index=True)
            new_df.sort_values(by="Download Date", ascending=True, inplace=True)

        if is_lineid:
            new_df.drop_duplicates(subset=["id"], inplace=True)
        else:
            new_df.drop_duplicates(subset=["url"], inplace=True)

        new_df.to_excel(db_path, index=False)
