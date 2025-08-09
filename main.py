from data.wind_utils import get_data_in_range

if __name__ == "__main__":
    data = get_data_in_range("AAPL.O", "2025-08-01", "2025-08-08")
    print(data)
