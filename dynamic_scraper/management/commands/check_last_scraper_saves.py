#Stage 2 Update (Python 3)
from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
import datetime
from optparse import make_option
from django.conf import settings
from django.core.mail import mail_admins
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from dynamic_scraper.models import Scraper

class Command(BaseCommand):
    help = 'Checks last item saves of a scraper being older than <last_scraper_save_alert_period> period provided in admin form'
    
    option_list = BaseCommand.option_list + (
        make_option(
            '--only-active',
            action="store_true",
            dest="only_active",
            default=False,
            help="Run scraper save checks only for active scrapers"),
        make_option(
            '--send-admin-mail',
            action="store_true",
            dest="send_admin_mail",
            default=False,
            help="Send report mail to Django admins if last saves are too old"),
        make_option(
            '--with-next-alert',
            action="store_true",
            dest="with_next_alert",
            default=False,
            help="Only run for scrapers with past next alert timestamp/update timestamp afterwards"),
    )
    
    
    def handle(self, *args, **options):
        mail_to_admins = False
        msg = ''
        
        if options.get('with_next_alert'):
            scrapers = Scraper.objects.filter(next_last_scraper_save_alert__lte=datetime.datetime.now())
        else:
            scrapers = Scraper.objects.all()
        
        for s in scrapers:
            td = s.get_last_scraper_save_alert_period_timedelta()
            if not (options.get('only_active') and s.status != 'A') and td:
                period = s.last_scraper_save_alert_period
                s_str = "SCRAPER: {scraper}\nID:{id}, Status:{status}, Alert Period:{period}".format(
                    scraper=str(s), id=s.pk, status=s.get_status_display(), period=period)
                print(s_str)
                
                if options.get('with_next_alert'):
                    s.next_last_scraper_save_alert = datetime.datetime.now() + td
                    s.save()
                
                if not s.last_scraper_save or \
                    (s.last_scraper_save < (datetime.datetime.now() - td)):
                    date_str = 'None'
                    if s.last_scraper_save:
                        error_str = "Last scraper save older than alert period ({date_str})!".format(
                            date_str=s.last_scraper_save.strftime('%Y-%m-%d %H:%m'),)
                    else:
                        error_str = "Last scraper save not available!"
                    print(error_str)
                    msg += s_str + '\n' + error_str + '\n\n'
                    mail_to_admins = True
                else:
                    print("OK")
                print()
        
        if options.get('send_admin_mail') and mail_to_admins:
            print("Send mail to admins...")
            if 'django.contrib.sites' in settings.INSTALLED_APPS:
                from django.contrib.sites.models import Site
                subject = Site.objects.get_current().name
            else:
                subject = 'DDS Scraper Site'
            subject += " - Last scraper save check for scraper(s) failed"
            
            mail_admins(subject, msg)