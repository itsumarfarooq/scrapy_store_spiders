import re
import scrapy

from scrapy_store_scrapers.utils import *



class LongandFoster(scrapy.Spider):
    name = "longandfoster"


    def start_requests(self) -> Iterable[Request]:
        yield scrapy.Request(
            url="https://www.longandfoster.com/pages/real-estate-offices",
            callback=self.parse
        )


    def parse(self, response: Response) -> Iterable[Dict]:
        pages = response.xpath("//div[@id='Master_dlCity']//a/@href").getall()
        for page in pages:
            yield scrapy.Request(
                url=page,
                callback=self.parse_page
            )


    def parse_page(self, response: Response) -> Iterable[Request]:
        offices = response.xpath("//div[@id='Master_dlCity']//a/@href").getall()
        for url in offices:
            yield scrapy.Request(
                url=url,
                callback=self.parse_office,
                cb_kwargs={"city_url": response.url}
            )


    def parse_office(self, response: Response, city_url: str) -> Iterable[Dict]:
        try:
            match = re.search(r"(?:stringify\()(.*?)(?:\);)", response.xpath("//script[contains(text(), 'officeJSONData')]/text()").get(), re.DOTALL)
            data = re.sub(r'\s+', " ", match.group(1)).replace("desc()",'"a"')
        except TypeError:
            self.logger.info("Office not found! {}, City: {}".format(response.url, city_url))
            return
        office = json.loads(data)
        yield {
            "number": re.search(r'(?:OfficeInfoPage\.init\()(.*?)(?:\);)', response.xpath("//script[contains(text(), 'OfficeInfoPage')]/text()").get(), re.DOTALL).group(1).split(",")[0].strip().strip('"'),
            "name": office['name'],
            "address": self._get_address(office),
            "location": self._get_location(response),
            "phone_number": office["telephone"],
            "url": response.url,
            "services": list(set(re.findall(r'(?:tileName\:\s\")(.*?)(?:\")', "\n".join(response.xpath("//script[contains(text(), 'serviceTiles.push')]/text()").getall())))),
            "raw": office
        }


    def _get_address(self, office: Dict) -> str:
        try:
            address_parts = [
                office['address']['streetAddress'].strip(),
            ]
            street = ", ".join(filter(None, address_parts))

            city = office['address']['addressLocality']
            state = office['address']['addressRegion']
            zipcode = office['address']['postalCode']

            city_state_zip = f"{city}, {state} {zipcode}".strip()

            return ", ".join(filter(None, [street, city_state_zip]))
        except Exception as e:
            self.logger.error("Error getting address: %s", e, exc_info=True)
            return ""


    def _get_location(self, response: Response) -> Dict:
        try:
            match = re.search(r'(?:OfficeInfoPage\.init\()(.*?)(?:\);)', response.xpath("//script[contains(text(), 'OfficeInfoPage')]/text()").get(), re.DOTALL)
            lat = float(match.group(1).split(",")[1].strip().strip('"'))
            lon = float(match.group(1).split(",")[2].strip().strip('"'))
            return {
                "type": "Point",
                "coordinates": [lon, lat]
            }
        except (ValueError, TypeError) as e:
            self.logger.error("Error getting location: %s", e, exc_info=True)
            return {}