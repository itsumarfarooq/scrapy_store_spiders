import scrapy
import json
from datetime import datetime
from typing import Dict, List, Any, Iterator
from scrapy_store_scrapers.items import SamsclubItem

class SamsclubSpider(scrapy.Spider):
    name = "samsclub"
    allowed_domains = ["www.samsclub.com"]

    def start_requests(self) -> Iterator[scrapy.Request]:
        url = "https://www.samsclub.com/api/node/vivaldi/browse/v2/clubfinder/search?isActive=true"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.samsclub.com/club-finder',
            'Origin': 'https://www.samsclub.com'
        }
        yield scrapy.Request(url=url, headers=headers, callback=self.parse)

    def parse(self, response: scrapy.http.Response) -> Iterator[scrapy.Request]:
        all_clubs = response.json()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.samsclub.com/club-finder',
            'Upgrade-Insecure-Requests': '1'
        }

        for club in all_clubs:
            club_url = f"https://www.samsclub.com/club/{club['clubId']}"
            yield scrapy.Request(url=club_url, headers=headers, callback=self.parse_club)
            break

    @staticmethod
    def convert_to_12_hour(time_str: str) -> str:
        time_obj = datetime.strptime(time_str, '%H:%M')
        return time_obj.strftime('%I:%M %p').lower()

    def parse_club(self, response: scrapy.http.Response) -> SamsclubItem:
        print(response.url)
        print(response.text)
        script_text = response.xpath('//script[@id="tb-djs-wml-redux-state"]/text()').get()
        data_dict = json.loads(script_text)
        raw_club_info = data_dict['clubDetails']
        club_id = raw_club_info['id']

        club_name = raw_club_info['name']
        club_phone = raw_club_info['phone']

        address = raw_club_info['address']

        club_address = address['address1']
        club_city = address['city']
        club_state = address['state']
        club_zip = address['postalCode']
        
        club_full_address = f"{club_address}, {club_city}, {club_state} {club_zip}"

        geo_info = raw_club_info['geoPoint']

        club_latitude = geo_info['latitude']
        club_longitude = geo_info['longitude']

        hours = raw_club_info['operationalHours']

        club_hours = {}

        for day, day_hours in hours.items():
            hours_dict = {
                'open': self.convert_to_12_hour(day_hours['startHrs']),
                'close': self.convert_to_12_hour(day_hours['endHrs'])
            }

            rename_dict = {
                'mondayHrs': 'monday',
                'tuesdayHrs': 'tuesday',
                'wednesdayHrs': 'wednesday',
                'thursdayHrs': 'thursday',
                'fridayHrs': 'friday',
                'saturdayHrs': 'saturday',
                'sundayHrs': 'sunday'
            }

            if day == 'monToFriHrs':
                week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
                for weekday in week_days:
                    club_hours[weekday] = hours_dict
            else:
                day = rename_dict[day]
                club_hours[day] = hours_dict

        # Define the correct order of days
        day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        # Sort club hours based on the defined order
        club_hours = {day: club_hours[day] for day in day_order if day in club_hours}
        
        services = response.xpath('//div[@class="bst-accordion-item-title"]/text()').getall()
        
        item = SamsclubItem(
            name=f"{club_name} #{club_id}",
            address=club_full_address,
            phone=club_phone,
            hours=club_hours,
            location={
                "type": "Point",
                "coordinates": [
                    club_longitude,
                    club_latitude
                ]
            },
            services=services
        )
        
        return item


        