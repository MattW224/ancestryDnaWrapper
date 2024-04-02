from collections import defaultdict
import json
import requests
import browser_cookie3
import sys

DEFAULT_ENDPOINT = "https://www.ancestry.com"

# Any of these filters can be combined.
INCLUSIVE_VALID_DNA_FILTERS = {
    "commonancestors",
    "messaged",
    "newmatches",
    "notviewed",
    "notes",
    "searchlocation",
    "searchname",
    "searchsurname",
    "searchsimilarsurname"
    "starredmatches"
}

# Exclusive in the sense that only one can be selected
# from each group, unless minshareddna and maxshareddna.
EXCLUSIVE_VALID_DNA_FILTERS = [
    {"publictrees", "privatetrees", "unlinkedtrees"},
    {"closematches", "distantmatches", "minshareddna", "maxshareddna"},
    {"maternalid", "paternalid"}
]
VALID_DNA_SORTS = {"DATE", "RELATIONSHIP"}


class ancestryDnaWrapper:
    def __init__(self, endpoint=DEFAULT_ENDPOINT):
        self._endpoint = endpoint
        self._session = self._authenticate(endpoint)

        self._matches_service = f"{endpoint}/discoveryui-matchesservice/api"

    def _authenticate(self, endpoint):
        AUTH_HEADERS = {
            "Content-Type": "application/json",
            # If get_dna_matches breaks, update this with value from web browser.
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"),
        }

        session = requests.session()
        # Inherit current authentication. Reverse engineering authentication is difficult --
        # tokens coming from ambiguous areas in /preauthenticate and /authenticate calls.
        try:
            browser_cookies = browser_cookie3.chrome()
        except PermissionError as e:
            print('Could not access browser cookies. An open browser window probably has a file lock on it. See Troubleshooting section in README.')
            print('\nRecommend logging into Ancestry on an unused browser (e.g. Edge), and change "browser_cookie3" library to inherit from there.')
            sys.exit(-1)

        session.cookies.update(browser_cookies)
        session.headers.update(AUTH_HEADERS)

        return session

    def _web_request(self, method, url, payload=None, query_string=None):
        web_request = getattr(self._session, method)
        response = web_request(
            url,
            data=json.dumps(payload),
            params=query_string)
        
        return json.loads(response.text)

    def _append_matches(self, collated_matches, match_groups):
        for group in match_groups:
            group_name = group["name"]["key"]
            collated_matches[group_name].extend(group["matches"])

        return collated_matches

    def _round_next_multiple(self, multiple, value):
        remainder = value % multiple

        if remainder > 0:
            return value + (multiple - remainder)
        else:
            return value + multiple

    def get_tests(self, test_type="completeTests"):
        response = self._session.get(f"{self._endpoint}/dna/secure/tests")
        tests = json.loads(response.text)

        filtered_tests = [test for test in tests["data"][test_type]]
        return filtered_tests

    def use_test(self, test_id):
        self._current_test = test_id

    def get_admixture(self, shared_match_test_id=None):
        if shared_match_test_id:
            endpoint = (f"{self._matches_service}/compare/{self._current_test}/with/{shared_match_test_id}/ethnicity")
        else:
            endpoint = (f"{self._endpoint}/dna/secure/tests/{self._current_test}/ethnicity")

        return self._web_request('get', endpoint)

    # Filter out all valid filters, then ensure set is empty.
    def validate_filters(self, sort_type, filters):
        if sort_type.upper() not in VALID_DNA_SORTS:
            raise ValueError(
                (f"sort_type value '{sort_type}' not accepted -- must be 'DATE' or 'RELATIONSHIP'."))

        selected_filter_types = set(filters.keys())
        selected_filter_types = selected_filter_types.difference(INCLUSIVE_VALID_DNA_FILTERS)

        for valid_filters in EXCLUSIVE_VALID_DNA_FILTERS:
            intersection = selected_filter_types.intersection(valid_filters)

            if len(intersection) == 2:
                MIN_SHARED_DNA = "minshareddna"
                MAX_SHARED_DNA = "maxshareddna"

                assert MIN_SHARED_DNA in selected_filter_types
                assert MAX_SHARED_DNA in selected_filter_types

                selected_filter_types.remove(MIN_SHARED_DNA)
                selected_filter_types.remove(MAX_SHARED_DNA)
            elif len(intersection) == 1:
                selected_filter_types.remove(intersection.pop())

        if len(selected_filter_types) > 0:
            raise ValueError(
                (f"Filters {selected_filter_types} not accepted. See README for valid filter types."))

    def get_dna_matches(
            self,
            sort_type="RELATIONSHIP",
            filters={},
            shared_match_test_id=None):
        matches = defaultdict(list)

        self.validate_filters(sort_type, filters)

        filters.update({
            "page": 1,
            "sortby": sort_type
        })

        if shared_match_test_id:
            filters.update({"relationguid": shared_match_test_id})

        endpoint = (f"{self._matches_service}/samples/{self._current_test}/matches/list")
        result = self._web_request('get', endpoint, query_string=filters)

        matches = self._append_matches(matches, result["matchGroups"])

        while result["bookmarkData"]["moreMatchesAvailable"]:
            previous_page = filters["page"]

            # Round to next multiple of five. Each API call returns up to
            # 200 results, with every fifty results constituting one page.
            filters["page"] = self._round_next_multiple(5, previous_page)

            filters.update(
                {
                    "bookmarkData": json.dumps({
                        "moreMatchesAvailable": True,
                        "lastMatchesServicePageIdx": previous_page
                    })
                }
            )

            result = self._web_request('get', endpoint, query_string=filters)
            matches = self._append_matches(matches, result["matchGroups"])

        return matches

    def get_common_ancestors(self, shared_match_test_id):
        endpoint = f"{self._matches_service}/compare/{self._current_test}/with/{shared_match_test_id}/commonancestors/"
        return self._web_request('get', endpoint)

    def get_tree_data(self, shared_match_test_id):
        endpoint = f"{self._matches_service}/compare/{self._current_test}/with/{shared_match_test_id}/treedata?generations=10"
        return self._web_request('get', endpoint)

    def get_custom_groups(self):
        endpoint = f"{self._matches_service}/samples/{self._current_test}/tags"
        return self._web_request('get', endpoint)

    def create_custom_group(self, group_name, group_hex_color):
        endpoint = f"{self._matches_service}/samples/{self._current_test}/tags"
        payload = {"tagName": group_name, "tagColor": group_hex_color}

        return self._web_request('post', endpoint, payload)

    def delete_custom_group(self, group_id):
        # Don't ask why these are empty values -- beats me.
        payload = {"removeTagFromAllMatchesResult": "", "deleteTagResult": ""}
        endpoint = (f"{self._matches_service}/samples/{self._current_test}/tags/{group_id}")

        return self._web_request('delete', endpoint, payload)

    def modify_group_membership(self, action, group_id, shared_match_test_id):
        action = action.lower().trim()

        if action == "add":
            endpoint = (f"{self._matches_service}/samples/{self._current_test}/{group_id}")
        elif action == "remove":
            endpoint = (f"{self._matches_service}/samples/{self._current_test}/matches/tags/{group_id}/remove")
        else:
            raise ValueError(
                "action value not accepted -- must be 'add' or 'remove'.")

        payload = {"matchSampleIds": [shared_match_test_id]}
        return self._web_request('post', endpoint, payload)

    def modify_star(self, action, shared_match_test_id):
        endpoint = (f"{self._matches_service}/samples/{self._current_test}/matches/{shared_match_test_id}")
        payload = {"starred": True} if action == "add" else {"starred": False}

        return self._web_request('post', endpoint, payload)
