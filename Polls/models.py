'''
Created on 18.04.2013

@author: aimiela
'''

import datetime

from random import random

from django.db import models
from django.db import IntegrityError
import md5


class BackendDB(models.Model):

    class Meta:
        abstract = True

    def _strip_vars(self, records_to_clean):
        for var_name, var_value in vars(self).iteritems():
            if var_name in records_to_clean and var_value:
                self.__setattr__(var_name, var_value.strip())


class Account(BackendDB):
    '''Unified account IDs (Drupal/CCD/SF).
    Used also as CCD/SF <-> Drupal IDs mapping
    for migrated B2C accounts.'''
    
    class Meta:
       app_label = 'Polls'

    id = models.AutoField(primary_key=True, null=False)  # PK
    # CCD/SF organization reference
    org_ref = models.CharField(max_length=10, null=True)
    # CCD/SF user reference
    usr_ref = models.CharField(max_length=10, null=True)
    # Drupal user ID reference (int(10))
    ext_usr_ref = models.IntegerField(null=True)
    # User creation date (local)
    created = models.DateTimeField(default=datetime.datetime.now, null=False)

    def save(self, *args, **kwargs):
        '''Enforces constrain: either CCD/SF or Drupal
        reference is to be provided!'''

        if self.org_ref is None and self.ext_usr_ref is None:
            raise models.exceptions.ValidationError()
        super(Account, self).save(*args, **kwargs)

    class Meta:
        '''Enforces that references are unique/indexes ext_usr_ref for
        search (may depend on database engine!)'''
        # TODO: check behavior on database engine migration!
        # creates unique on these fields!
        unique_together = ('ext_usr_ref', 'org_ref', 'usr_ref')


class Session(BackendDB):
    '''External session ID lookup table.'''
   
    # PK
    id = models.AutoField(primary_key=True, null=False)
    # Drupal session ID (varchar(43))
    ext_session_ref = models.CharField(max_length=50, default=None, null=False)
    # Session creation timestamp according to the external system
    ext_session_timestamp = models.DateTimeField(null=True)
    # Creation timestamp
    created = models.DateTimeField(default=datetime.datetime.now, null=False)

    class Meta:
        unique_together = ('ext_session_ref', 'ext_session_timestamp')
        app_label = 'Polls'


class SessionAccount(BackendDB):
    '''Stores session_id <-> account_id relationship.'''
    # PK (must be provided)
    id = models.AutoField(primary_key=True, null=False)
    # session_id
    session = models.ForeignKey(Session)
    # account ID
    sub_account = models.ForeignKey(Account,
                                    related_name='session_sub_account',
                                    null=True)
    # backend account ID (backend/B2B customers only!)
    account = models.ForeignKey(Account)
    # Creation timestamp

    created = models.DateTimeField(default=datetime.datetime.now, null=False)

    class Meta:
        unique_together = ('session', 'account', 'sub_account')
        app_label = 'Polls'


class Login(BackendDB):
    '''Stores CCD/SF logins.'''

    class RIGHTS:
        WEBSITE_ACCESS = 1
        MOBILE_ACCESS = 2

    login = models.EmailField(primary_key=True, default=None, null=False)                   # Login name (e-mail address); PK!
    account = models.ForeignKey(Account)                                                    # main company's account ID
    sub_account = models.ForeignKey(Account, related_name='login_sub_account', null=True)   # employee's account ID
    pwd_hash = models.CharField(max_length=50, null=True)                                   # 1st password (automatic, MD5 hash)
    plain_pwd = models.CharField(max_length=50, null=True)                                  # 2nd password (plain - for CS/test purposes only)
    role = models.IntegerField(default=0, null=False)                                       # Defined by frontend!
    rights = models.IntegerField(default=0, null=False)                                     # Bit-encoded: 1=website, 2=mobile access
    created = models.DateTimeField(default=datetime.datetime.now, null=False)             # Creation timestamp
    class Meta:
		app_label = 'Polls'

class Requester(BackendDB):
    '''Stores requesters/originators to identify the direct/indirect service caller.'''

    id = models.AutoField(primary_key=True, null=False)                     # requester ID (PK)
    desc = models.CharField(max_length=50, default=None, null=False)        # description
    legal_entity = models.CharField(max_length=2, default=None, null=False)  # CARFAX legal entity (country ISO code)
    class Meta:
		app_label = 'Polls'

class RC(BackendDB):
    '''Registers each record check attempt.'''

    id = models.AutoField(primary_key=True, null=False)                                 # Record Check ID (PK)
    session = models.ForeignKey(Session, null=True)                                     # session_id
    account = models.ForeignKey(Account, null=True)                                     # account_id
    sub_account = models.ForeignKey(Account, related_name='rc_sub_account', null=True)  # sub_account_id
    role = models.IntegerField(null=True)                                               # Defined by frontend!
    req = models.ForeignKey(Requester, related_name='req_id')                           # Requester (website?)
    src_req = models.ForeignKey(Requester, null=True, related_name='src_req_id')        # Source requester ID (forwarder)
    query = models.CharField(max_length=50, default=None, null=False)                   # User query
    created = models.DateTimeField(default=datetime.datetime.now)                     # Creation timestamp
    class Meta:
		app_label = 'Polls'

class ReportType(BackendDB):
    '''All available report types.'''

    id = models.CharField(max_length=20, primary_key=True, null=False)      # 'VHR_SE_SV_HTML' - see initial_data fixture for details
    ccd_ag_req_pattern = models.URLField(null=True, max_length=250)         # Pattern to build CCD-alike AG request (backwards compatibility/used for log maintenance)
    expiration_days = models.IntegerField(null=True)                        # Expiration days (if relevant)
    class Meta:
		app_label = 'Polls'
		
class Condition(BackendDB):
    id = models.CharField(max_length=20, primary_key=True, null=False)          # 'SE_VHR_SINGLE' - see initial_data fixture for details
    requester = models.ForeignKey(Requester, null=True)                         # Requester (country reference)
    qty_limit = models.IntegerField(null=True)                                  # Quantity limit (if relevant)
    expiration_days = models.IntegerField(null=True)                            # Expiration days (if relevant)
    lock_threshold = models.IntegerField(null=True)                             # Threshold (the exact meaning is condition specific) to activate account lock (T&C violation?)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)     # Gross price (if relevant)
    net_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # Net price (if relevant)
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, null=True)   # VAT rate (if relevant)
    vat_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # VAT value (if relevant)
    currency = models.CharField(max_length=3, null=True)                        # Currency (if relevant)

    def save(self, *args, **kwargs):
        '''Calculates (if needed) tax-related values.'''

        if self.price and self.net_price is None and self.vat_rate is None and self.vat_value is None:
            if self.id.startswith('SE'):
                vat_rate = 25
            else:
                vat_rate = 19
            net_price = round(100 * self.price / (100 + vat_rate), 2)
            vat_value = self.price - net_price

            self.price = '%.2f' % self.price
            self.net_price = '%.2f' % net_price
            self.vat_rate = '%.2f' % vat_rate
            self.vat_value = '%.2f' % vat_value

            args = (True, False) + args[2:]  # force_insert, force_update
            kwargs.pop('force_insert', None)
            kwargs.pop('force_update', None)
        return super(Condition, self).save(args, **kwargs)


class ReportCondition(BackendDB):
    '''Associates available reports with belonging conditions.'''

    id = models.AutoField(primary_key=True, null=False)
    report_type = models.ForeignKey(ReportType, null=False)
    condition = models.ForeignKey(Condition, null=False)
    req = models.ForeignKey(Requester, null=True)

    class Meta:
        '''Enforces unique references.'''
# TODO: check behavior on database engine migration!
        unique_together = ('report_type', 'condition', 'req')  # creates unique index on these fields!
        app_label = 'Polls'
		
		
class RcResult(BackendDB):
    id = models.AutoField(primary_key=True, null=False)                    # Record Check alternative ID (PK)
    rc = models.ForeignKey(RC)                                             # Record Check reference
    report_type = models.ForeignKey(ReportType)                            # ReportType ID
    report_ref = models.CharField(max_length=50, default=None, null=False)  # Unique report reference (usually a VIN)
    report_records = models.IntegerField(null=True)                        # NULL=request failed; -1=unknown; 0=no records found; otherwise - number of VHR records
    report_options = models.IntegerField(null=True)                        # NULL=request failed/not applicable; 1=US link available

#    country = models.CharField(max_length=2, null=False)                  # Country ISO code
#    lang = models.CharField(max_length=2, null=False)


class TransactionReferenceBase(BackendDB):
    '''Abstract parameters of an unique "human readable" transaction references for grouping related Transaction records and issuing receipts.'''

    ALLOWED_PK_CHARACTERS = '34679ACDEFGHJKLMNPRTUVWXY'  # removed: 0/O/Q, 1/I, 2/Z, 5/S, B/8
    PK_LENGTH = 8
    MAX_PK_TRIES = 5

    class Meta:
        abstract = True


class TransactionReference(TransactionReferenceBase):
    '''Provides unique "human readable" transaction references for grouping related Transaction records.'''

    id = models.CharField(max_length=TransactionReferenceBase.PK_LENGTH, primary_key=True, null=False)  # PK
    created = models.DateTimeField(default=datetime.datetime.now, null=False)                         # Creation timestamp

    def __get_id(self):
        '''Generates randomly a new alpha-numerical token using ALLOWED_PK_CHARACTERS/PK_LENGTH constrains.'''

        new_id = u''
        for _ in range(self.PK_LENGTH):
            new_id += self.ALLOWED_PK_CHARACTERS[int(random() * len(self.ALLOWED_PK_CHARACTERS))]
        return new_id

    def save(self, *args, **kwargs):
        '''Generates a new key automatically.'''

        if self.pk:
            return super(TransactionReference, self).save(*args, **kwargs)
        else:
            # Django ORM clean-up...
            args = (True, False) + args[2:]  # force_insert, force_update
            kwargs.pop('force_insert', None)
            kwargs.pop('force_update', None)
            # ...Django ORM clean-up
            for _ in range(self.MAX_PK_TRIES):
                try:
                    self.pk = self.__get_id()
                    return super(TransactionReference, self).save(args, **kwargs)
                except IntegrityError:
                    pass
                except:
                    raise
            else:
# TODO: consider a dedicated/own exception
                raise IntegrityError


class Token(BackendDB):
    '''Stores CCD tokens. Might be used also for supporting US and PDF links.'''

    MAX_PK_TRIES = 3

    id = models.CharField(max_length=32, primary_key=True)   # PK

    def __get_id(self):
        '''Generates a random MD5 hash'''
        return md5.md5('%s%s' % (unicode(random()), unicode(datetime.datetime.now()))).hexdigest()

    def save(self, *args, **kwargs):
        '''Generates a new key automatically.'''
        if self.pk:
            return super(Token, self).save(*args, **kwargs)
        else:
            # Django ORM clean-up...
            args = (True, False) + args[2:]  # force_insert, force_update
            kwargs.pop('force_insert', None)
            kwargs.pop('force_update', None)
            # ...Django ORM clean-up
            for _ in range(self.MAX_PK_TRIES):
                try:
                    self.pk = self.__get_id()
                    return super(Token, self).save(args, **kwargs)
                except IntegrityError:
                    pass
                except:
                    raise
            else:
# TODO: consider a dedicated/own exception
                raise IntegrityError


class Report(BackendDB):
    '''Stores report data.'''

    id = models.AutoField(primary_key=True, null=False)                         # PK

    account = models.ForeignKey(Account)                                        # Account reference
    report_type = models.ForeignKey(ReportType)                                 # Report type
    report_ref = models.CharField(max_length=50, default=None, null=False)      # Report reference (usually a VIN)

    query = models.CharField(max_length=50, default=None, null=False)           # Original user query

    expires_on = models.DateTimeField(null=True)                                # Expiration date
    created = models.DateTimeField(default=datetime.datetime.now, null=False)  # Creation timestamp
    ccd_ag_req = models.URLField(null=True, max_length=250)                     # CCD-alike AG request (backwards compatibility/used for log maintenance)
    parent = models.ForeignKey('Report', null=True, default=None)               # Parent report reference for linked reports (like US links)
    token = models.ForeignKey(Token, null=True, unique=True)                    # Report token

    class Meta:
        unique_together = ('account', 'report_type', 'report_ref')              # To ensure the same report is not pulled more than once!
        app_label = 'Polls'

class Asset(BackendDB):
    id = models.AutoField(primary_key=True, null=False)                         # PK
    ext_asset_ref = models.CharField(max_length=18, default=None, null=False)   # SF ID sample: 001D000000kL4UdIAK
    account = models.ForeignKey(Account)                                        # account_id (company's account ID for b2b)
    condition = models.ForeignKey(Condition, null=True)                         # Condition reference
    qty = models.IntegerField(null=True)                                        # Quantity (if relevant)
    start_date = models.DateTimeField(null=True)                                # Install date
    end_date = models.DateTimeField(null=True)                                  # Usage end date
    created = models.DateTimeField(default=datetime.datetime.now, null=False)  # Creation timestamp
    updated = models.DateTimeField(auto_now=True, null=False)                   # Updated timestamp
    inactive = models.IntegerField(default=0, null=False)                       # Bit-encoded: 1=cancelled

    class Meta:
        unique_together = ('ext_asset_ref', 'condition')                        # To ensure the same report is not pulled more than once!
        app_label = 'Polls'

class Transaction(BackendDB):
    '''Stores transactions: credits, purchases & more.'''

    id = models.AutoField(primary_key=True, null=False)                                             # PK
    t_ref = models.ForeignKey(TransactionReference)                                                 # Transaction reference (to group related transactions)
    account = models.ForeignKey(Account)                                                            # account_id (company's account ID for b2b)
    sub_account = models.ForeignKey(Account, related_name='transaction_sub_account', null=True)   # employee's account ID (applicable for b2b only)
    role = models.IntegerField(default=None, null=True)                                             # Defined by frontend MIGHT BE DELETED
    t_type = models.IntegerField(default=0, null=False)                                             # Transaction type: 1xx=credits; 2xx=pulls;
    requester = models.ForeignKey(Requester, null=True)                                             # Requester (website) reference
    condition = models.ForeignKey(Condition, null=True)                                             # Condition reference
    rcresult = models.ForeignKey(RcResult, null=True)                                               # RC result reference
    report = models.ForeignKey(Report, null=True)                                                   # Report related directly to the transaction (if any)
    ext_t_ref = models.CharField(max_length=50, null=True)                                          # External transaction reference
    qty = models.IntegerField(null=True)                                                            # Quantity (if relevant)
    expires_on = models.DateTimeField(null=True)                                                    # Expiration date
    created = models.DateTimeField(default=datetime.datetime.now, null=False)                     # Creation timestamp
    asset = models.ForeignKey(Asset, null=True)                                                     # Asset reference
    class Meta:
		app_label = 'Polls'

class Report_Archive(BackendDB):
    '''Stores report data.'''

    id = models.IntegerField(primary_key=True, null=False)                      # PK

    account_id = models.IntegerField(null=False)                                # Account reference
    report_type_id = models.CharField(max_length=20, default=None, null=False)  # Report type
    report_ref = models.CharField(max_length=50, default=None, null=False)      # Report reference (usually a VIN)

    query = models.CharField(max_length=50, default=None, null=False)           # Original user query

    expires_on = models.DateTimeField(null=True)                                # Expiration date
    created = models.DateTimeField(null=False)                                  # Creation timestamp
    ccd_ag_req = models.URLField(null=True, max_length=250)                     # CCD-alike AG request (backwards compatibility/used for log maintenance)
    parent = models.ForeignKey('Report_Archive', null=True, default=None)       # Parent report reference for linked reports (like US links)
    token_id = models.CharField(max_length=32, null=True)                       # Report token
    batch = models.ForeignKey('Batch', null=False)                              # Maintenance batch archiving the report
    class Meta:
		app_label = 'Polls'

class TransactionReport(BackendDB):

    id = models.AutoField(primary_key=True, null=False)                     # PK
    transaction = models.ForeignKey(Transaction)
    report = models.ForeignKey(Report_Archive)
    batch = models.ForeignKey('Batch', null=False)                          # Maintenance batch archiving the report
    class Meta:
		app_label = 'Polls'
#===============================================================================
# Receipt
#=========================================================================


class Receipt(TransactionReferenceBase):
    '''Stores issued receipts/freezing actual purchase conditions.

    WARNING: for better performance there is no constrain Receipt.id->TransactionReference.id!
    It has to be enforced by the code.'''

    id = models.CharField(max_length=TransactionReferenceBase.PK_LENGTH, primary_key=True, null=False)   # PK
    transaction = models.ForeignKey(Transaction)                                                         # Transaction id
    price = models.DecimalField(max_digits=10, decimal_places=2, null=False)                             # Gross price (if relevant)
    net_price = models.DecimalField(max_digits=10, decimal_places=2, null=False)                         # Net price (if relevant)
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, null=False)                           # VAT rate (if relevant)
    vat_value = models.DecimalField(max_digits=10, decimal_places=2, null=False)                         # VAT value (if relevant)
    currency = models.CharField(max_length=3, default=None, null=False)                                  # Currency (if relevant)
    class Meta:
		app_label = 'Polls'
#===============================================================================
# Batch
#=========================================================================


class Batch(BackendDB):
    '''Stores batch details (backend maintenance tasks).'''

    id = models.AutoField(primary_key=True, null=False)       # PK
    created = models.DateTimeField(auto_now=True, null=False)
    class Meta:
		app_label = 'Polls'
#=========================================================================
# Payment: Viatel
#=========================================================================


class ViatelBatch(BackendDB):
    '''Stores Viatel code generation batch details.'''

    class INACTIVE_BITS:
        TEST = 1
        CANCELLED = 2

    batch = models.ForeignKey('Batch', primary_key=True, null=False)    # generation batch reference
    valid_from = models.DateTimeField(null=True)                        # Validity from
    valid_to = models.DateTimeField(null=True)                          # Validity to
    inactive = models.IntegerField(default=0, null=False)               # Bit-encoded: see INACTIVE_BITS
    condition = models.ForeignKey(Condition, null=True)                 # condition reference
    prn = models.CharField(max_length=50, null=True)                    # PRN number
    comment = models.CharField(max_length=250, null=True)               # Comment
    class Meta:
		app_label = 'Polls'

class ViatelCode(BackendDB):
    '''Generated Viatel codes.'''

    ALLOWED_PK_CHARACTERS = (
                            (u'123456789'),    # pos 1
                            (u'0123456789'),   # pos 2
                            (u'0123456789'),   # pos ...
                            (u'0123456789'),
                            (u'0123456789'),
                            (u'0123456789'),
    )
    # virtually no limit (6 => chance to fail: ~0.5% on
    # 10000 codes/45000 already existing)
    MAX_PK_TRIES = 100
    CODE_LENGTH = 6

    code = models.CharField(primary_key=True, max_length=CODE_LENGTH, default=None, null=False)  # code (PK)
    batch = models.ForeignKey('ViatelBatch', null=False)                                        # batch id

    def __get_id(self):
        '''Generates randomly a new numerical code using ALLOWED_PK_CHARACTERS/CODE_LENGTH constrains.'''

        new_id = u''
        for pos in range(self.CODE_LENGTH):
            new_id += self.ALLOWED_PK_CHARACTERS[pos][int(random() * len(self.ALLOWED_PK_CHARACTERS[pos]))]
        return new_id

    def save(self, *args, **kwargs):
        '''Generates a new key automatically.'''
        if self.pk:
            return super(ViatelCode, self).save(*args, **kwargs)
        else:
            # Django ORM clean-up...
            args = (True, False) + args[2:]  # force_insert, force_update
            kwargs.pop('force_insert', None)
            kwargs.pop('force_update', None)
            # ...Django ORM clean-up
            for _ in range(self.MAX_PK_TRIES):
                try:
                    self.pk = self.__get_id()
                    return super(ViatelCode, self).save(args, **kwargs)
                except IntegrityError, e:
                    if e[0] in (
                        1062,  # Duplicate entry '?' for key 'PRIMARY'
                    ):
                        pass
                    else:
                        raise
                except:
                    raise
            else:
                raise IntegrityError('Failed to generate a unique code after %i attempt(s)' % self.MAX_PK_TRIES)


class ViatelUsedCode(BackendDB):
    '''Stores utilized Viatel codes.'''

    # PK
    code = models.ForeignKey('ViatelCode', primary_key=True, null=False)  # TODO: add account_id/sub_account_id/session_id?
    used_up = models.DateTimeField(auto_now=True, null=False)            # timestamp


class ViatelLog(BackendDB):
    '''Stores Viatel log (for HTTP notitication listener!).'''

    id = models.AutoField(primary_key=True, null=False)                         # PK

    prn = models.CharField(max_length=50, default=None, null=False)             # called PRN=Premium Rate Number
    input = models.CharField(max_length=250, null=True, db_index=True)          # input=code
    caller = models.CharField(max_length=50, null=True)                         # caller number
    time = models.DateTimeField(null=False)                                     # call time stamp (finish)
    rate = models.DecimalField(max_digits=5, decimal_places=0, null=False)      # call cost in "cents"
    currency = models.CharField(max_length=3, default=None, null=False)         # currency (ISO 3-chars)
    ratetype = models.CharField(max_length=3, default=None, null=False)         # transaction type: PPC=Price Per Call or PPM=Pcide Per Minute
    duration = models.IntegerField(null=False)                                  # call duration in seconds
    repeats = models.IntegerField(null=False)                                   # message repetition counter (0=no repetition/said once)
    protected = models.BooleanField(null=False)                                 # protected caller number = yes/no
    created = models.DateTimeField(default=datetime.datetime.now,
                                   null=False)  # log creation date

    @classmethod
    def get_field_names(cls):
        for field in cls._meta.fields:
            yield field.name
    class Meta:
		app_label = 'Polls'
#===========================================================================
# class Transaction_Archive(Transaction):
#    pass
#===========================================================================

#===========================================================================
# class Voucher(BackendDB):
#    '''Vouchers probably not needed for now.'''
#    pass
#
# class Backend(object):
#
#    def transaction_b2b_rollover_all(self):
#        pass
#
#    def transaction_archive_all(self):
#        pass
#
#    def reports_archive_all(self):
#        pass
#==========================================================================
