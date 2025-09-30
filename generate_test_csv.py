import csv
import random
from datetime import datetime, timedelta

def generate_test_csv(filename="test_10k_products.csv", count=10000):
    categories = ["Electronics", "Books", "Clothing", "Home", "Sports", "Toys", "Food", "Beauty"]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow(["name", "description", "price", "stock", "category", "auth_email"])
        
        # 10,000 records
        for i in range(count):
            writer.writerow([
                f"Product_{i+1:05d}",
                f"Test product description {i+1}",
                round(random.uniform(10.0, 999.99), 2),
                random.randint(0, 1000),
                random.choice(categories),
                "test@load-test.com"
            ])
    
    print(f"✅ {count} recordos CSV fájl létrehozva: {filename}")

if __name__ == "__main__":
    generate_test_csv()
