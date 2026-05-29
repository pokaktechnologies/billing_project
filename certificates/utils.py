CERTIFICATE_SUFFIX = {
    'Internship': 'INT',
    'Job Training': 'JTR',
    'Experience': 'EXP',
    'Employee': 'EMP',
    'Webinar': 'WEB',
    'Internship College': 'INC',
}

def generate_certificate_number(certificate_type):
    from certificates.models import CertificateRecord

    suffix = CERTIFICATE_SUFFIX.get(certificate_type, 'CERT')
    prefix = f"CERT-{suffix}-"

    last = CertificateRecord.objects.filter(
        certificate_number__startswith=prefix
    ).order_by('-certificate_number').first()

    if last:
        last_number = int(last.certificate_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{str(new_number).zfill(5)}"