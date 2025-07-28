from app.services import put_apartment_info_from_realt_to_mongo


def realt_parser():
    put_apartment_info_from_realt_to_mongo()


if __name__ == "__main__":
    realt_parser()
