import os
import logging
import time
import requests

from .coorcal import generate_coordinate

logging.basicConfig(
    level=logging.ERROR, format='%(levelname)s: %(message)s')

try:
    CLIENT_ID = os.environ['CLIENT_ID']
    CLIENT_SECRET = os.environ['CLIENT_SECRET']
except KeyError as e:
    logging.error('You must have client\'s id and secret in environment first')

TODAY = time.strftime("%Y-%m-%d")
BASE_URL = 'https://graph.facebook.com/'
API_VERSION = 'v2.9/'
TOKEN_PATH = 'oauth/access_token?client_id={0}&client_secret={1}&&'\
              'grant_type=client_credentials'.format(CLIENT_ID, CLIENT_SECRET)
SEARCH_PAGE_PATH = 'search?type=place&q={0}&center={1},{2}'\
                    '&distance={3}&limit={4}&fields=id&access_token={5}'

EVENT_FIELDS = ['id',
                'name',
                'start_time',
                'description',
                'place',
                'type',
                'category',
                'ticket_uri',
                'cover.fields(id,source)',
                'picture.type(large)',
                'attending_count',
                'declined_count',
                'maybe_count',
                'noreply_count']

PAGE_FIELDS = ['id',
               'name',
               'cover.fields(id,source)',
               'picture.type(large)',
               'location']

# Get App Access Token
token = requests.get(BASE_URL +
                     API_VERSION +
                     TOKEN_PATH).json()['access_token']


def get_page_ids(latitude, longitude, query_agrument='*',
                 distance=500, limit=100):
    '''
    Get pages's ID from a circle of locations. Return a list of all ID.

    :param latitude: Latitude of location's center
    :param longitude: Longitude of location's center
    :param query_agrument: Type of Page you want to get events from.
        '*' mean all types.
    :param distance: Radius of location's circle. Limit for better speed.
    :param limit: Pagination limit. You should let it by default.
    '''
    pages_id = requests.get(BASE_URL +
                            API_VERSION +
                            SEARCH_PAGE_PATH.format(
                                query_agrument,
                                latitude,
                                longitude,
                                distance,
                                limit,
                                token
                                )
                            ).json()

    pages_id_list = [i['id'] for i in pages_id['data']]

    # Process Facebook API paging
    while 'paging' in pages_id:
        if 'next' in pages_id['paging']:
            pages_id = requests.get(pages_id["paging"]['next']).json()
            for a in pages_id['data']:
                pages_id_list.append(a['id'])

    return pages_id_list


def get_events(page_id, base_time=TODAY, fields=EVENT_FIELDS):
    '''
    For each page ID, find all events (if have any) of that Page
    from given time.

    Return a dictionary of page's infos and it's events.

    :param page_id: ID of page
    :param base_time: Limit started day to crawl events. Format: YYYY-MM-DD
    :param fields: List of event's fields. See more at
        https://developers.facebook.com/docs/graph-api/reference/event
    '''
    events = requests.get(BASE_URL + API_VERSION,
                          params={
                            "ids": page_id,
                            "fields": """
                                      events.fields({0}).since({1})
                                      """.format(','.join(fields), base_time),
                            "access_token": token,
                          })

    return events.json()


def get_events_by_location(latitude, longitude, place_type='*',
                           distance=500, limit=100, scan_radius=200,
                           base_time=TODAY, fields=EVENT_FIELDS):
    """
    Get all events from given location circle.

    :param latitude: Latitude of location's center
    :param longitude: Longitude of location's center
    :param event_type: Type of Page you want to get events from. '*' mean all.
    :param distance: Radius of location's circle. Limit for better speed.
    :param limit: Pagination limit. You should let it by default.
    :param base_time: Limit started day to crawl events. Format: YYYY-MM-DD
    :param fields: List of event's field. See more at
        https://developers.facebook.com/docs/graph-api/reference/event
    """
    CIRCLE = (latitude, longitude, distance, )
    events = []

    for point in generate_coordinate(*CIRCLE, scan_radius=scan_radius):
        page_list = get_page_ids(latitude, longitude, place_type,
                                 distance, limit)
        for page_id in page_list:
            nodes = get_events(page_id, base_time=base_time,
                               fields=fields)[page_id]
            if 'events' in nodes:
                events.append(nodes['events']['data'])
            else:
                pass

    return events


def get_page_info(page_id, fields=PAGE_FIELDS):
    """
    Get info of given Page ID

    :param page_id: ID of page
    :param fields: See more here
        https://developers.facebook.com/docs/graph-api/reference/page
    """
    info = requests.get(BASE_URL + API_VERSION,
                        params={
                            'ids': page_id,
                            'fields': ','.join(fields),
                            'access_token': token
                        }).json()
    return info