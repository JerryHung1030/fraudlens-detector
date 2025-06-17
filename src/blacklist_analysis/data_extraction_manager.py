import requests
import json
import os
import pandas as pd
from datetime import datetime, timezone
from dateutil import parser
from urllib.parse import urlparse
import whois


class DataExtractionManager:
    def __init__(self):
        pass
        
    def get_info_from_file(self, input_files, output_file):
        for input_file in input_files:
            good_bad_flag = input_file["good_bad"]
            df_input = pd.read_excel(input_file["filename"])
            
            results = []
            
            for idx, row in df_input.iterrows():
                url = str(row.get("url"))
                found_date = row.get("Found Date")
                download_date = row.get("Download Date")
                source = row.get("Source")
                
                parsed = urlparse(url)
                domain = parsed.hostname or url
                domain = domain.lower().strip()
                
                if not domain or "." not in domain:
                    print(f"[WARNING] bad domain, skip:{url}")
                    continue
                
                tld = self.get_tld(domain)
                
                info = {
                    'url': url,
                    'domain': domain,
                    'tlds': tld,
                    'source': source,
                    'found_date': found_date,
                    'download_date': download_date,
                    'good/bad': good_bad_flag,
                    'whois_success': False,
                    'whois_hasdata': False,
                    'creation_date': None,
                    'expiration_date': None,
                    'updated_date': None,
                    'register time': None,
                    'remaining time': None,
                    'total life time': None,
                    'register_country': None,
                    'registrar_exist': False,
                    'email_exist': False,
                    'name_exist': False,
                    'org_exist': False,
                    'address_exist': False,
                    'dnssec': "unknown"
                }
        
                try:
                    print(f"[INFO] processing: {domain}")
                    whois_data = whois.whois(domain)

                    if not whois_data or isinstance(whois_data, str):
                        raise ValueError("Empty or invalid WHOIS data")

                    info['whois_success'] = True

                    creation_date_raw = whois_data.get("creation_date")
                    
                    if creation_date_raw is None:
                        raise ValueError("No creation date available")

                    creation_date = self.extract_datetime(creation_date_raw, "min")
                    info['whois_hasdata'] = True
                    
                    reference_date = self.get_reference_date(found_date)
                    expiration_date = self.extract_datetime(whois_data.get("expiration_date"), "max")
                    updated_date = self.extract_datetime(whois_data.get("updated_date"), "max")

                    info['creation_date'] = creation_date
                    info['expiration_date'] = expiration_date
                    info['updated_date'] = updated_date
                    
                    info['register time'] = (reference_date - creation_date).days if creation_date else None
                    info['remaining time'] = (expiration_date - reference_date).days if expiration_date else None
                    info['total life time'] = (expiration_date - creation_date).days if expiration_date else None
                    info['register_country'] = whois_data.get("country", "Unknown")

                    if whois_data.get("registrar"):
                        info['registrar_exist'] = True
                    if whois_data.get("email") or whois_data.get("emails") or whois_data.get("registrant_email"):
                        info['email_exist'] = True
                    if whois_data.get("name") or whois_data.get("registrant_name"):
                        info['name_exist'] = True
                    if whois_data.get("org") or whois_data.get("organization"):
                        info['org_exist'] = True
                    if whois_data.get("address"):
                        info['address_exist'] = True
                    if whois_data.get("dnssec") is not None:
                        info['dnssec'] = whois_data.get("dnssec")

                except Exception as e:
                    print(f"[ERROR] failed to get whois data for {url}: {e}")

                results.append(info)

            result_df = pd.DataFrame(results)

            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            if os.path.exists(output_file):
                existing_df = pd.read_excel(output_file)
                full_df = pd.concat([existing_df, result_df], ignore_index=True).drop_duplicates()
            else:
                full_df = result_df

            full_df.to_excel(output_file, index=False)
            print(f"[SUCCESS] {output_file} done: Total: {len(full_df)}")
    
    def get_tld(self, domain):
        return domain.split(".")[-1].lower() if "." in domain else ""
    
    def extract_datetime(self, dates, pick='min'):
        try:
            if not dates:
                return None

            if isinstance(dates, list):
                parsed_dates = []
                for d in dates:
                    if isinstance(d, datetime):
                        dt = d
                    else:
                        dt = parser.parse(d)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    parsed_dates.append(dt)
                if not parsed_dates:
                    return None
                dt = min(parsed_dates) if pick == 'min' else max(parsed_dates)
            else:
                if isinstance(dates, datetime):
                    dt = dates
                else:
                    dt = parser.parse(dates)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

            return dt.date()
        except Exception as e:
            return None

    def get_reference_date(self, found_date):
        try:
            if pd.isna(found_date) or found_date is None or str(found_date).strip().lower() in ["", "nan", "none"]:
                return datetime.now(timezone.utc).date()

            if isinstance(found_date, (datetime, pd.Timestamp)):
                return found_date.date()
            elif isinstance(found_date, int):
                found_date = str(found_date)

            dt = parser.parse(str(found_date))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.date()

        except Exception as e:
            print(f"[WARNING] failed to parse {found_date}, Error: {e}")
            return datetime.now(timezone.utc).date()
