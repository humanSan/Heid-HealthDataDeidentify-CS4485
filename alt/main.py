from matchers.addresses import strip_addresses
from matchers.dates import strip_dates
from matchers.emails import strip_emails
from matchers.names import strip_names
from matchers.phonenums import strip_phone_nums
from matchers.ssn import strip_ssn

with open("ehr JMS.txt", "r") as file:
    txt = file.read()

    # strip sensitive information
    txt = strip_dates(txt)
    txt = strip_emails(txt)
    txt = strip_phone_nums(txt)
    txt = strip_names(txt)
    txt = strip_ssn(txt)
    txt = strip_addresses(txt)

    print(txt)

    with open('out.txt', 'w') as output:
        output.write(txt)
        output.close()