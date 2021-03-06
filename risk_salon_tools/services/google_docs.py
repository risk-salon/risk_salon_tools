import gspread
import logging
import httplib2
import time

import apiclient.discovery as discovery

import pandas as pd

from oauth2client.service_account import ServiceAccountCredentials
from risk_salon_tools.services.config import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# TODO refactor to super-class with authentication


class SheetsClient(object):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    def __init__(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
                      Settings().get('google_docs_api_credentials_filepath'), self.scope)

        self.gc = gspread.authorize(credentials)

    def get_df(self, sheet_name):
        wks = self.gc.open(sheet_name).sheet1
        return pd.DataFrame(wks.get_all_records())


class DriveClient(object):
    scope = 'https://www.googleapis.com/auth/drive'

    logger = logging.getLogger('googleapiclient.discovery')
    logger.setLevel(logging.INFO)

    def __init__(self):
        self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
            Settings().get('google_docs_api_credentials_filepath'), self.scope)
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('drive', 'v3', http=self.http)

    def grant_permissions(self, file_id, email_addresses, role='commenter'):
        try:
            assert(role in ['writer', 'commenter', 'reader'])
        except AssertionError:
            logger.error('Invalid role: must be one of writer, commenter, reader.')

        def callback(request_id, response, exception):
            if exception:
                # Handle error
                logger.error(exception)
            else:
                logger.info("Permission Id: %s" % response.get('id'))


        # sharing will fail to non-Google accounts
        for email_address in email_addresses:
            batch = self.service.new_batch_http_request(callback=callback)
            logger.info('Trying to give {} {} role.'.format(email_address, role))
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email_address
            }
            batch.add(self.service.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields='id',
            ))

            # TODO better error handling when execute() fails
            batch.execute()

            time.sleep(0.05)
