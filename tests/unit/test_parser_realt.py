import types
import pytest

from app.parsers import realt_apartments_parser


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeSession:
    """Замена requests.Session"""
    def __init__(self, html_by_url: dict[str, str]):
        self._html_by_url = html_by_url

    def get(self, url: str, headers=None):
        html = self._html_by_url.get(url)

        if html is None:
            raise AssertionError(f"Unexpected get {url}")
        return _FakeResponse(html)


@pytest.fixture(autouse=True)
def patch_useragent(monkeypatch):
    """Фиксирует заголовок"""
    class _UserAgent:
        random = "UnitTestAgent/1.0"

    monkeypatch.setattr(realt_apartments_parser.fake_useragent, "UserAgent", lambda: _UserAgent())
    return None


def test_parse_all_apartments_ids_happy_path(monkeypatch):
    listing_url = "https://realt.by/belarus/sale/flats/?page=1&sortType=createdAt"
    listing_html = """
        <html><body>
          <div class="t-0 l-0 absolute w-full">
            <div data-index="1">
              <span class="relative z-[2]">ID 123456</span>
              <a class="z-1 absolute top-0 left-0 w-full h-full cursor-pointer"
                 href="/belarus/sale-flats/object/123456/">link</a>
            </div>
            <div data-index="2">
              <span class="relative z-[2]">ID 777</span>
              <a class="z-1 absolute top-0 left-0 w-full h-full cursor-pointer"
                 href="/belarus/sale-flats/object/777/">link</a>
            </div>
          </div>
        </body></html>
        """

    fake = _FakeSession({listing_url: listing_html})
    monkeypatch.setattr(realt_apartments_parser.requests, "Session", lambda: fake)

    out = realt_apartments_parser.parse_all_apartments_ids_from_realt()
    assert isinstance(out, list)
    assert out == [
        {"_id": "123456", "link": "https://realt.by/belarus/sale-flats/object/123456/", "state": "first"},
        {"_id": "777", "link": "https://realt.by/belarus/sale-flats/object/777/", "state": "first"},
    ]


def test_parse_all_apartments_ids_returns_empty_when_block_missing(monkeypatch):
    listing_url = "https://realt.by/belarus/sale/flats/?page=1&sortType=createdAt"
    html_without_block = "<html><body><div>no target block</div></body></html>"
    fake = _FakeSession({listing_url: html_without_block})
    monkeypatch.setattr(realt_apartments_parser.requests, "Session", lambda: fake)

    out = realt_apartments_parser.parse_all_apartments_ids_from_realt()
    assert out == []


def test_parse_apartment_data_from_realt_full(monkeypatch):
    card_url = "https://realt.by/brest-region/sale-flats/object/3824111/"
    card_html = """
    <html><body>
      <h1 class="order-1 mb-0.5 md:-order-2 md:mb-4 block w-full !inline-block lg:text-h1Lg text-h1 font-raleway font-bold flex items-center">
        Квартира&nbsp;2-комнатная
      </h1>
      <h2 class="!inline-block mr-1 lg:text-h2Lg text-h2 font-raleway font-bold flex items-center">
        100&nbsp;000&nbsp;$ 
      </h2>

      <ul class="w-full -my-1">
        <li>
          <span class="text-basic">Город</span>
          <div class="w-1/2"><p>—</p></div>
          <div class="w-1/2"><p>Минск</p></div>
        </li>
        <li>
          <span class="text-basic">Ссылка продавца</span>
          <div class="w-1/2"></div>
          <div class="w-1/2"><a href="https://example.com">realt.by</a></div>
        </li>
      </ul>
    </body></html>
    """

    fake = _FakeSession({card_url: card_html})
    monkeypatch.setattr(realt_apartments_parser.requests, "Session", lambda: fake)

    out = realt_apartments_parser.parse_apartment_data_from_realt(card_url)

    assert out["title"] == "Квартира 2-комнатная"          # NBSP заменён
    assert out["price"] == "100 000 $"                      # NBSP заменён
    assert out["Город"] == "Минск"
    assert out["Ссылка продавца"] == "realt.by"
    assert out["state"] == "second"
    assert out["link"] == card_url


def test_parse_apartment_data_from_realt_when_value_only_in_anchor(monkeypatch):
    card_url = "https://realt.by/some/object/1/"
    card_html = """
    <html><body>
      <h1 class="order-1 mb-0.5 md:-order-2 md:mb-4 block w-full !inline-block lg:text-h1Lg text-h1 font-raleway font-bold flex items-center">Тайтл</h1>
      <h2 class="!inline-block mr-1 lg:text-h2Lg text-h2 font-raleway font-bold flex items-center">1&nbsp;$</h2>
      <ul class="w-full -my-1">
        <li>
          <span class="text-basic">Сайт</span>
          <div class="w-1/2"></div>
          <div class="w-1/2"><a href="#">example&nbsp;site</a></div>
        </li>
      </ul>
    </body></html>
    """
    fake = _FakeSession({card_url: card_html})
    monkeypatch.setattr(realt_apartments_parser.requests, "Session", lambda: fake)

    out = realt_apartments_parser.parse_apartment_data_from_realt(card_url)
    assert out["Сайт"] == "example site"  # NBSP обработан
    assert out["price"] == "1 $"
