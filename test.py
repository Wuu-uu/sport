try:
    from bs4 import BeautifulSoup
    print("BeautifulSoup4 安裝正確！")
except ImportError as e:
    print(f"錯誤：{e}")
    