import asyncio
import os
import csv
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Ubah angka ini sesuai keinginan
max_data = 200

# Tambahkan query yang diinginkan di sini
queries = ["Pabrik Snack, Andir"]

async def searchGoogleMaps(query, max_data):
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{query}.csv')
    zona = query.split(",")[-1].strip()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto(f'https://www.google.com/maps/search/{"+".join(query.split())}')
            await page.wait_for_selector('div[role="feed"]')
            await autoScrollSearchResults(page)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and "/maps/place/" in href:
                    if href.startswith('/'):
                        href = 'https://www.google.com' + href
                    results.append(href)
                    if len(results) >= max_data:
                        break
            
            businesses = []
            for index, result_url in enumerate(results):
                try:
                    print(f"Processing result {index + 1}/{len(results)}")
                    
                    detail_url = result_url
                    print(f"Visiting detail URL: {detail_url}")
                    await page.goto(detail_url)
                    await page.wait_for_selector('div[role="main"]')
                    await autoScrollDetail(page)
                    
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    parent = soup.find('div', {'role': 'main'})
                    name_elem = parent.find('h1')
                    name = name_elem.get_text().strip() if name_elem else None
                    
                    category_elem = parent.find('button', class_='DkEaL')
                    category = category_elem.get_text().strip() if category_elem else None
                    
                    phone_elem = parent.find('button', {'data-tooltip': 'Salin nomor telepon'})
                    phone = phone_elem.get_text().strip().replace('î‚°', '') if phone_elem else None
                    phone = ''.join(filter(str.isdigit, phone)) if phone else None
                    
                    website_elem = parent.find('a', class_='CsEnBe', href=True)
                    website = website_elem.get('href') if website_elem else None
                    
                    address_elem = parent.find('div', class_='Io6YTe fontBodyMedium kR99db')
                    address = address_elem.get_text().strip().replace('îƒˆ', '') if address_elem else None
                    
                    ratingText_elem = parent.find('span', class_='fontBodyMedium')
                    ratingText = ratingText_elem.get_text() if ratingText_elem else None
                    if ratingText:
                        ratingText = ratingText.replace(',', '.')
                    
                    try:
                        stars = float(ratingText.split(' ')[0]) if ratingText else None
                        numberOfReviews = int(ratingText.split(' ')[1].replace(',', '')) if ratingText else None
                    except (ValueError, IndexError):
                        stars = None
                        numberOfReviews = None
                    
                    businesses.append({
                        'Name': name,
                        'Category': category,
                        'Phone': phone,
                        'Website': website,
                        'Address': address,
                        'Rating': ratingText,
                        'Verified': 'Ya' if parent.find('span', class_='UY7F9') else 'Tidak',
                        'Zona': zona,
                        'Map URL': detail_url
                    })
                    
                    # Tulis data ke file CSV setiap selesai memproses satu entri
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['Name', 'Category', 'Phone', 'Website', 'Address', 'Rating', 'Verified', 'Zona', 'Map URL']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(businesses)
                    
                    await page.go_back()
                    await page.wait_for_selector('div[role="feed"]')
                    
                    if len(businesses) >= max_data:
                        break
                
                except Exception as e:
                    print(f"Error saat memproses detail URL: {detail_url}, Error: {e}")
                    continue
            
        except Exception as e:
            print(f"Error pada searchGoogleMaps: {e}")
        
        finally:
            # Tutup browser
            await browser.close()

async def autoScrollSearchResults(page):
    await page.evaluate('''async () => {
        await new Promise((resolve, reject) => {
            var totalHeight = 0;
            var distance = 1000;
            var scrollDelay = 3000;

            var timer = setInterval(async () => {
                var wrapper = document.querySelector('div[role="feed"]');
                if (!wrapper) {
                    reject('Wrapper element not found');
                    return;
                }
                var scrollHeightBefore = wrapper.scrollHeight;
                wrapper.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeightBefore) {
                    totalHeight = 0;
                    await new Promise((resolve) => setTimeout(resolve, scrollDelay));

                    var scrollHeightAfter = wrapper.scrollHeight;

                    if (scrollHeightAfter > scrollHeightBefore) {
                        return;
                    } else {
                        clearInterval(timer);
                        resolve();
                    }
                }
            }, 200);
        });
    }''')

async def autoScrollDetail(page):
    await page.evaluate('''async () => {
        await new Promise((resolve, reject) => {
            var wrapper = document.querySelector('div[role="main"]');
            if (!wrapper) {
                reject('Wrapper element not found');
                return;
            }
            var totalHeight = 0;
            var distance = 1000;
            var scrollDelay = 3000;

            var timer = setInterval(async () => {
                var scrollHeightBefore = wrapper.scrollHeight;
                wrapper.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeightBefore) {
                    totalHeight = 0;
                    await new Promise((resolve) => setTimeout(resolve, scrollDelay));

                    var scrollHeightAfter = wrapper.scrollHeight;

                    if (scrollHeightAfter > scrollHeightBefore) {
                        return;
                    } else {
                        clearInterval(timer);
                        resolve();
                    }
                }
            }, 200);
        });
    }''')

async def main():
    for query in queries:
        await searchGoogleMaps(query, max_data)

if __name__ == "__main__":
    asyncio.run(main())
