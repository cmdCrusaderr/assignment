def normalise_email(email):
    if not email:
        return None
    email = email.strip().lower()
    return email


def normalise_phone(phone):
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        return None
    return digits[-10:]


CITY_ALIASES = {
    "gurugram": "gurgaon",
    "new delhi": "delhi",
    "delhi ncr": "delhi",
    "bengaluru": "bangalore",
}

def normalise_city(city):
    if not city:
        return None
    city = city.strip().lower()
    return CITY_ALIASES.get(city, city)

if __name__ == "__main__":
    email_cases = [
        "ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG",
        "isha.chopra95@mailtest.example.org",
        "  tanvi.gupta31@example.com  ",
    ]
    phone_cases = [
        "9000000254", "+919000000254", "09000000254", "919000000254", "+91-9000000131",
    ]
    city_cases = [
        "GURGAON", "Gurgaon", "gurugram ", "Delhi NCR", "new delhi", "Delhi", "Bengaluru", "bangalore",
    ]

    print("-- emails --")
    for e in email_cases:
        print(f"{e!r:45} -> {normalise_email(e)!r}")

    print("\n-- phones --")
    for p in phone_cases:
        print(f"{p!r:20} -> {normalise_phone(p)!r}")

    print("\n-- cities --")
    for c in city_cases:
        print(f"{c!r:15} -> {normalise_city(c)!r}")
