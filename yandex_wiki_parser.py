import os
import re
import requests
from urllib.parse import urljoin
from datetime import datetime
import json
import shutil

class YandexWikiParser:
    BASE_URL = "https://wiki.yandex.ru/"
    USER_AGENT = "PostmanRuntime/7.39.0"

    def __init__(self, csrf_token, yc_session, directory=""):
        if directory == "":
            directory = f"{os.getcwd()}{os.sep}data"
        
        self.__session = requests.Session()
        self.__cookies = self.__generate_cookies(csrf_token, yc_session)
        self.__headers = self.__generate_headers(csrf_token)
        self.__navigation_tree = {}
        self.__url_pages = []
        self.__url_attachments = []
        self.__directory = f"{directory}\\{self.__generate_directory_name()}"
        self.__md_directory = os.path.join(self.__directory, "pages_markdown")
        self.__metadata_directory = os.path.join(self.__directory, "pages_metadata")
        self.__attachments_directory = os.path.join(self.__directory, "attachments")

    def create_backup(self):
        if os.path.exists(self.__directory):
            shutil.rmtree(self.__directory)
        
        self.__fetch_navigation_tree()
        self.__download_md()
        self.__download_metadata()
        self.__copy_pages_for_RAG()
        self.__download_attachments()
        
    def __generate_cookies(self, csrf_token, yc_session):
        return {
            "CSRF-TOKEN": csrf_token,
            "yc_session": yc_session
        }

    def __generate_headers(self, csrf_token):
        return {
            "User-Agent": self.USER_AGENT,
            "X-CSRF-Token": csrf_token.replace("%3A", ":"),
            "x-collab-org-id": self.__fetch_collab_org_id()
        }

    def __fetch_collab_org_id(self):
        response = self.__session.get(self.BASE_URL, headers={}, cookies=self.__cookies)
        match = re.search(r'"collabOrgId":"(.*?)"', response.text)
        if not match:
            raise ValueError("Unauthorized")
        return match.group(1)

    def __generate_directory_name(self):
        current_date = datetime.now().strftime("%Y_%m_%d")
        return f"{current_date}"

    def __fetch_navigation_tree(self):
        self.__navigation_tree = {'slug': '', 'title': '', 'full_title': '', 'has_children': True, 'children': []}
        self.__fetch_navigation_tree_recursive(self.__navigation_tree)
        self.__extract_pages_url()

    def __fetch_navigation_tree_recursive(self, node):
        if not node['has_children']:
            return node

        children = self.__fetch_navigation_tree_children(node['slug'])

        for child in children:
            child['full_title'] = f"{child['title'].strip('.')}."
            if node['full_title']:
                child['full_title'] = f"{node['full_title']} {child['full_title']}"

            self.__fetch_navigation_tree_recursive(child)

        node['children'] = children
        return node

    def __fetch_navigation_tree_children(self, parent_slug):
        url = urljoin(self.BASE_URL, ".gateway/root/wiki/openNavigationTreeNode")
        response = self.__session.post(url, json={"parentSlug": parent_slug}, headers=self.__headers,
                                       cookies=self.__cookies)
        response_json = response.json()
        children = response_json.get('children', {}).get('results', [])
        return children

    def __extract_pages_url(self):
        self.__url_pages = []
        self.__extract_pages_url_recursive(self.__navigation_tree, self.__url_pages)
        print(f"Found {len(self.__url_pages)} pages")

    def __extract_pages_url_recursive(self, node, urls):
        for child in node.get('children', []):
            self.__extract_pages_url_recursive(child, urls)
            page_url = urljoin(self.BASE_URL, child['slug'])
            urls.append(page_url)
        return urls

    def __download_md(self):
        if not os.path.exists(self.__md_directory):
            os.makedirs(self.__md_directory)

        for url in self.__url_pages:
            response = self.__session.get(url, headers=self.__headers, cookies=self.__cookies)
            match = re.search(r'"content":"(.*?)","owner":', response.text)
            if not match:
                print(f"Downloading page markdown skipped: {url}")
                continue

            raw_content = match.group(1)
            formatted_content = raw_content.replace(self.BASE_URL, "/").replace("\\n", "\n")
            file_name = url.replace(self.BASE_URL, "").replace("/", "\\")
            file_path = os.path.join(self.__md_directory, f"{file_name}.md")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(formatted_content)
            print(f"Downloaded page markdown: {url} -> {file_path}")

    def __download_metadata(self):
        if not os.path.exists(self.__metadata_directory):
            os.makedirs(self.__metadata_directory)
        
        for url in self.__url_pages:
            response = self.__session.get(url, headers=self.__headers, cookies=self.__cookies)
            metadata = self.__fetch_page_metadata(response.text, url)
            file_name = url.replace(self.BASE_URL, "").replace("/", "\\")
            file_path = os.path.join(self.__metadata_directory, f"{file_name}.json")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(metadata, file, indent=4, ensure_ascii=False)
            print(f"Downloaded page metadata: {url} -> {file_path}")

    def __fetch_page_metadata(self, response_text, url):
        slug = url.replace(self.BASE_URL, "")
        node = self.__get_node_by_slug_recursive(self.__navigation_tree, slug)
        
        metadata = {
            "title": self.__extract_with_regex(response_text, r'<title>(.*?) \| Wiki<\/title>'),
            "full_title": node['full_title'],
            "relative_url": url.replace(self.BASE_URL, "/"),
            "username": self.__extract_with_regex(response_text, r'"username":"(.*?)"'),
            "display_name": self.__extract_with_regex(response_text, r'"display_name":"(.*?)"'),
            "created_at": self.__extract_with_regex(response_text, r'"created_at":"(.*?)"')
        }
        return metadata

    def __get_node_by_slug_recursive(self, node, slug):
        if node['slug'] == slug:
            return node

        for child in node.get('children', []):
            result = self.__get_node_by_slug_recursive(child, slug)
            if result is not None:
                return result
        
        return None
    
    def __extract_with_regex(self, text, pattern):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def __download_attachments(self):
        self.__search_attachments()
        
        if not os.path.exists(self.__attachments_directory):
            os.makedirs(self.__attachments_directory)

        for url in self.__url_attachments:
            response = self.__session.get(url, headers=self.__headers, cookies=self.__cookies)
            file_name = url.replace(self.BASE_URL, "").replace("/", "\\")
            file_path = os.path.join(self.__attachments_directory, file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as file:
                file.write(response.content)
            print(f"Downloaded attachment: {url} -> {file_path}")

    def __search_attachments(self):
        md_files = self.__get_files(self.__md_directory, ".md")
        for file_path in md_files:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                matches = re.findall(r'!\[.*?\]\((\/\S*)', content) + re.findall(r'{% file src="(\/\S*)"', content)
                full_urls = [urljoin(self.BASE_URL, match) for match in matches]
                self.__url_attachments.extend(full_urls)
        print(f"Found {len(self.__url_attachments)} attachments")

    def __copy_pages_for_RAG(self, banned_directory = 'users'):
        self.__flatten_directory(self.__md_directory, ".md", f"{self.__md_directory}_RAG{os.sep}", 'users')
        self.__flatten_directory(self.__metadata_directory, ".json", f"{self.__metadata_directory}_RAG{os.sep}", 'users')
        print(f"Copied pages for RAG")
    
    def __flatten_directory(self, directory, extension, destination_directory, skip_directory):
        os.makedirs(os.path.dirname(destination_directory), exist_ok=True)
        found_files = self.__get_files(directory, extension)
        for file_path in found_files:
            if skip_directory in file_path.split(os.sep):
                continue

            flat_filename = os.path.relpath(file_path, start = directory).replace(os.sep, '_')
            shutil.copy(file_path, os.path.join(destination_directory, flat_filename))

    def __get_files(self, directory, extension):
        found_files = []
        for root, _, files in os.walk(directory):
            for file_name in files:
                if file_name.endswith(extension):
                    found_files.append(os.path.join(root, file_name))
        return found_files

def main():
    # csrf_token = "1a61a3ed7d30bbad486409c6bcc1edf24e74a54e%3A1720980869"
    # yc_session = "c1.9euelZqUj43Hk4vKnJWLmJqOnI6ezu3rnpWazpGKls7GzcmQzYqKlp7Lx8zl9Pd8VC9L-e94MH2q3fT3HCwuS_nveDB9qtXo9fKGnNGQnoqLl9GIlpSW7fmQj5qRlpvN1_XbycfLz5rGyMjSzM3OzNLLz83I0seayM3Sx87Kz87IxsnGmZme7_7F656VmpKXyZOVnJHIzcnHnZuejJXM.Twg1PcnfU63jEOR1lmHz0s80q5Bx4uXjMa6FtCzB_q87zHqlMMqHFad8-8r3ha8JGGwpjI0LdQR3k_LkABEZBg"
    # directory = ""

    csrf_token = input("Введите CSRF-TOKEN: ")
    yc_session = input("Введите yc_session: ")
    directory = input("Введите каталог загрузки: ")
    
    try:
        parser = YandexWikiParser(csrf_token, yc_session, directory)
        parser.create_backup()

    except ValueError as e:
        print(e)

if __name__ == "__main__":
    main()
