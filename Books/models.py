from django.db import models
from Polls.models import (Transaction, Account, Report, Report_Archive,
                            TransactionReport, Login)
from collections import defaultdict
from Polls.util.vts import VtsLinkGenerator
from Polls.logger import Logger
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


logger = Logger()
vts_link_gen = VtsLinkGenerator(logger)


class EmptyReport(object):

    def __init__(self):
        self._fixed_attrs = {'id': -1, }
        self.active = False
        self.vts_link = None

    def __getattr__(self, attr):
        return self._fixed_attrs.get(attr, 'Unknown')


class FrontendPaymentItem(models.Model):
    class Meta:
        #app_label = 'backofficedddddddddddddddddd'
        db_table = 'carfax_payment_item'

    cpid = models.IntegerField(primary_key=True)
    coid = models.CharField(max_length=16)
    mail = models.CharField(max_length=64)
    amount = models.FloatField()
    package = models.CharField(max_length=32)
    status = models.CharField(max_length=1)
    timestamp = models.DateTimeField()
    vin = models.CharField(max_length=32)
    report_ref = models.CharField(max_length=32)


    def __str__(self):
        return "%s: %s" % (self.coid, self.mail)

class FrontendUser(models.Model):

    CREDIT_RANGE = range(100, 199)

    class Meta:
        #app_label = 'backoffice'
        db_table = 'users'

    uid = models.IntegerField(primary_key=True)
    mail = models.CharField(max_length=254)
    created = models.IntegerField()
    login = models.IntegerField()

    def clean(self):
        all_emails = [login.login for login in Login.objects.all()]
        if self.mail in all_emails:
            raise ValidationError("This email already exists as a B2B user!")
        validate_email(self.mail)

    def packages(self, show_archived_reports=False):
        if not hasattr(self, 'packages_container'):
            try:
                acc = Account.objects.get(ext_usr_ref=self.uid)
            except Account.DoesNotExist:
                self.packages_container = []
                return self.packages_container

            packages_container = []
            reports = defaultdict(list)
            pulled_report_count = defaultdict(int)
            for transaction in Transaction.objects.filter(account=acc).order_by('-id'):
                if transaction.t_type in FrontendUser.CREDIT_RANGE:
                    packages_container.append(transaction)
                elif transaction.t_type == 200:
                    pulled_report_count[transaction.t_ref_id] += 1
                    if transaction.report_id:
                        report = Report.objects.get(pk=transaction.report_id)
                        report.active = True
                        report.vts_link = vts_link_gen.get_vts_link(report)
                        reports[transaction.t_ref_id].append(report)
                    elif show_archived_reports:
                        for report in Report_Archive.objects.filter(id__in=[tr.report_id for tr in TransactionReport.objects.filter(transaction_id=transaction.id)]):
                            report.active = False
                            report.vts_link = vts_link_gen.get_vts_link(report)
                            reports[transaction.t_ref_id].append(report)
                    else:
                        continue

            for transaction in packages_container:
                transaction.reports = sorted(reports.get(transaction.t_ref_id, []), key=lambda x: x.id, reverse=True)
                transaction.remaining_credits = transaction.qty - pulled_report_count.get(transaction.t_ref_id, 0) if not transaction.condition_id.endswith('UNLIMITED') else 'INF'

            self.packages_container = list(packages_container)

        return self.packages_container

    def payments(self):
        if not hasattr(self, 'payments_container'):
            self.payments_container = list(FrontendPaymentItem.objects.filter(mail=self.mail).order_by('-cpid'))

        return self.payments_container



def not_existing_frontend_user(mail_addr):
    return FrontendUser(
        uid=-1,
        mail=mail_addr,
        created=0,
    )
