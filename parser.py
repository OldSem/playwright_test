import json
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright, Route, Request


class Parser:
    """Class for parsing a Twitter (X) profile using Playwright."""

    TWIT_COUNT: int = 50  # Maximum number of tweets to extract

    def __init__(self, path: str = 'https://x.com/elonmusk') -> None:
        """
        Initialize the parser with a Twitter profile URL.

        :param path: The URL of the Twitter profile to scrape.
        """
        self.url: str = path  # Store the profile URL
        self.data: Dict[str, Any] = {}  # Dictionary to store extracted data

    def get_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract profile information from the intercepted API response.

        :param data: The JSON response from the intercepted API request.
        :return: A dictionary containing user profile details.
        """
        profile: Dict[str, Any] = data['data']['user']['result']['legacy']
        user_data: Dict[str, Any] = {
            'username': profile.get('screen_name'),  # Twitter handle (e.g., @elonmusk)
            'display_name': profile.get('name'),  # Full display name
            'followers': profile.get('followers_count'),  # Number of followers
            'following': profile.get('friends_count'),  # Number of accounts followed
            'tweets_count': profile.get('statuses_count'),  # Total tweet count
            'profile_url': profile.get('profile_banner_url'),  # Profile banner image
            'avatar': profile.get('profile_image_url_https')  # Profile picture URL
        }
        return user_data

    def tweet_parse(self, legacy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant information from a tweet.

        :param legacy: The dictionary containing tweet details.
        :return: A dictionary containing parsed tweet data.
        """
        tweet: Dict[str, Any] = {
            'created_at': legacy['created_at'],  # Timestamp of the tweet
            'text': legacy['full_text'],  # Full text of the tweet
            'quote_count': legacy['quote_count'],  # Number of quotes
            'reply_count': legacy['reply_count'],  # Number of replies
            'retweet_count': legacy['retweet_count'],  # Number of retweets
            'bookmark_count': legacy.get('bookmark_count', 0),  # Number of bookmarks (default 0)
        }

        # Extract media URLs if available
        tweet_media = legacy.get('entities', {}).get('media', [])
        if tweet_media:
            media: List[Dict[str, str]] = [{'url': item['media_url_https']} for item in tweet_media]
            tweet['media'] = media  # Add media to tweet dictionary

        return tweet

    def get_tweets(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tweets from the API response.

        :param data: The JSON response containing tweets.
        :return: A list of dictionaries, each containing tweet data.
        """
        instructions: List[Dict[str, Any]] = data['data']['user']['result']['timeline_v2']['timeline']['instructions']
        tweets: List[Dict[str, Any]] = []

        # Extract first tweet
        first_tweet_legacy = instructions[1]['entry']['content']['itemContent']['tweet_results']['result']['legacy']
        tweets.append(self.tweet_parse(first_tweet_legacy))

        # Extract remaining tweets
        original_tweets: List[Dict[str, Any]] = instructions[2]['entries']
        for tweet in original_tweets[:self.TWIT_COUNT - 1]:  # Limit tweets to TWIT_COUNT
            legacy = tweet['content']['itemContent']['tweet_results']['result']['legacy']
            tweets.append(self.tweet_parse(legacy))  # Parse and add to the list

        return tweets

    def save_results(self, path: str = 'profile.json') -> None:
        """
        Save extracted data to a JSON file.

        :param path: The file path where the results should be saved.
        """
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)  # Pretty-print JSON

    def intercept_request(self, route: Route, request: Request) -> None:
        """
        Intercept GraphQL API requests and extract profile/tweet data.

        :param route: The Playwright route object.
        :param request: The intercepted request object.
        """

        def query() -> Dict[str, Any]:
            """Fetch and return the JSON response from the request."""
            print(route)
            response = route.fetch()  # Fetch response without modifying it
            return response.json()  # Convert response to JSON

        if "UserByScreenName" in request.url:  # Profile data request
            self.data['user'] = self.get_profile(query())

        if "UserTweets" in request.url:  # Tweets data request
            self.data['tweets'] = self.get_tweets(query())

        route.continue_()  # Continue normal request processing

    def parse(self) -> None:
        """
        Launch Playwright, intercept API requests, and extract data.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Open a visible browser
            context = browser.new_context()
            page = context.new_page()

            # Intercept GraphQL API requests to extract profile & tweets
            page.route("**/graphql/**", self.intercept_request)

            # Open the Twitter profile page
            page.goto(self.url, wait_until="networkidle")

            # Wait a few seconds for tweets to load
            page.wait_for_timeout(7000)

            browser.close()

    def run(self) -> None:
        """
        Run the parser: fetch data and save results.
        """
        self.parse()
        self.save_results()