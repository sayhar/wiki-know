#!/usr/bin/env python3
import csv
from os.path import isfile, join, basename
from os import walk
import urllib.request
import urllib.error
from random import choice, shuffle
from glob import glob
from time import strftime, gmtime
import re

# app_helper.py
# called by app_functions.py and hello.py

GUESSNODIFF = "__guess_no_difference__"


class AppHelper:
    def __init__(self, theapp, s3):
        self.app = theapp
        self.alltests_cache = dict()
        self.NOSHOT = list()
        if s3:
            try:
                import flask_s3

                self.url_for = flask_s3.url_for
            except ImportError:
                # Fallback to regular Flask url_for if flask_s3 is not available
                import flask

                self.url_for = flask.url_for
        else:
            import flask

            self.url_for = flask.url_for

    # PUBLIC FACING:
    def get_guessnone(self):
        return GUESSNODIFF

    def win_dir(self, testname):
        # Given a testname, return a winner row and a dirname
        dirname = join("static", "report", testname)
        winner_row = self._get_row(dirname)
        return winner_row, dirname

    def row_stats(self, winner_row):
        d = dict()
        d["win_by"] = float(winner_row["bestguess"])
        d["lowerbound"] = float(winner_row["lowerbound"])
        d["upperbound"] = float(winner_row["upperbound"])
        d["variable"] = winner_row["var"]
        d["country"] = winner_row["country"]
        d["language"] = winner_row["language"]
        try:
            d["dollar_pct"] = float(winner_row["dollarimprovementpct"])
            d["lower_dollar"] = float(winner_row["dollarlowerpct"])
            d["upper_dollar"] = float(winner_row["dollarupperpct"])
            d["campaign"] = winner_row["campaign"]
        except (ValueError, KeyError):
            d["dollar_pct"] = "Not calculated"
            d["lower_dollar"] = "Not calculated"
            d["upper_dollar"] = "Not calculated"
            d["campaign"] = "Unknown"
        date = winner_row["time"]
        date = gmtime(float(date))
        d["date"] = strftime("%a, %d %b %Y %H:%M:%S UTC", date)
        return d

    def guess_stats(self, winner_row, dirname, guess=None):
        d = dict()
        isconfidence = self._is_confident(winner_row)
        d["isconfidence"] = isconfidence
        d["guessedcorrectly"], d["leancorrectly"], d["winner"], d["loser"] = (
            self._true_results(winner_row, dirname, isconfidence, guess)
        )
        return d

    def get_info(self, dirname):
        infofile = "info.txt"
        try:
            with open(join(dirname, infofile), "r") as fin:
                infotext = fin.read()
        except FileNotFoundError:
            # probably no such file
            infotext = ""
        return infotext

    def get_tables(self, filename):
        tables = []
        report_files = ["reportA.html", "reportB.html", "reportD.html", "reportE.html"]

        try:
            for report_file in report_files:
                with open(join(filename, report_file), "r") as f:
                    tables.append(f.read())
        except FileNotFoundError:
            try:
                with open(filename + "report.html", "r") as f:
                    tables = f.read()
            except FileNotFoundError:
                tables = "notable"
        return tables

    def graph_local(self, testname, graphname):
        use_local = False
        file_or_url_name = join("report", testname, graphname)
        exists, isurl = self._exists_and_is_url(
            self.url_for("static", filename=file_or_url_name)
        )
        # if it's not on the server, fallback to trying local file
        if not exists and isurl:
            use_local = True
        return use_local

    def get_diag_graphs(self, testname):
        diag_types = self._diagnostic_types(testname)
        diag = {}
        for diag_type in diag_types:
            diagnostic_num, use_local_diag = self._max_diagnostic_num(
                testname, diag_type
            )
            diag[diag_type] = {"num": diagnostic_num, "local": use_local_diag}
        return diag

    def get_diagnostic_charts(self, directory):
        # currently this should return nothing:
        names = glob(directory + "/diagnostic_data*.html")
        toreturn = []
        for name in names:
            try:
                with open(name, "r") as f:
                    toreturn.append(f.read())
            except FileNotFoundError:
                continue
        return toreturn

    def next_test(self, thistest, batch):
        # assume all_tests is already sorted, so we just need to find the next one.
        if not self.test_in_batch(thistest, batch):
            return "wrong batch"
        alltests = self.all_tests(batch)
        thisindex = alltests.index(thistest)
        nextindex = thisindex + 1
        if nextindex < len(alltests):
            next_test = alltests[nextindex]
        else:
            # return None
            next_test = "fin"
        return next_test

    def prev_test(self, thistest, batch):
        # assume all_tests is already sorted, so we just need to find the next one.
        if not self.test_in_batch(thistest, batch):
            return "wrong batch"
        alltests = self.all_tests(batch)
        thisindex = alltests.index(thistest)
        previndex = thisindex - 1
        if previndex > 0:
            prev = alltests[previndex]
        else:
            return None
        return prev

    def screenshot_lines(self, dirname):
        try:
            with open(join(dirname, "screenshots.csv"), "r") as fin:
                reader = csv.reader(fin, delimiter=",")
                next(reader)  # Skip header
                lines = list(reader)
        except FileNotFoundError:
            return dict(error=True, why="No such test: " + dirname)

        # so "lines" = lines in screenshots.csv

        if len(set(list(zip(*lines))[1])) != 2:
            # if there are not 2 variations
            return dict(error=True, why="Wrong number of screenshots: " + dirname)

        return dict(error=False, lines=lines)

    def find_screenshots_and_names(self, dirname, lines):
        screenshots = {}
        longnames = {}
        # manytype: if there are multiple screenshots, is it multivariate or combo?
        manytype = "multivariate"
        # remember, 'line' = line in screenshots.csv

        for line in lines:
            varname = line[1]
            desc = self._real_value(varname, dirname)
            longnames[varname] = desc  # No need for decode in Python 3
            thisshot = line[3]

            # Get testname from the directory
            testname = basename(dirname)

            # Convert imgur URLs to S3 URLs with fallback logic
            if thisshot != "NA" and thisshot.startswith("http://i.imgur.com"):
                thisshot = self._get_s3_screenshot_url(thisshot, testname, varname)
            elif thisshot != "NA" and not thisshot.startswith("http://i.imgur.com"):
                # Non-imgur URLs should be left unchanged
                pass

            if line[1] in screenshots:
                if thisshot != "NA":
                    if thisshot not in screenshots[varname]:
                        screenshots[varname].append(thisshot)
                    if line[4] != "NA":
                        manytype = "combo"
                        extra_shot = line[4]
                        # Convert extra screenshot URLs too
                        if extra_shot.startswith("http://i.imgur.com"):
                            extra_shot = self._get_s3_imgur_fallback_url(extra_shot)
                        if extra_shot not in screenshots[varname]:
                            screenshots[varname].append(extra_shot)
                    # screenshots[varname] = list(set(screenshots[varname]))
            else:
                if thisshot != "NA":
                    screenshots[varname] = [thisshot]
                    if line[4] != "NA":
                        manytype = "combo"
                        extra_shot = line[4]
                        # Convert extra screenshot URLs too
                        if extra_shot.startswith("http://i.imgur.com"):
                            extra_shot = self._get_s3_imgur_fallback_url(extra_shot)
                        screenshots[varname].append(extra_shot)
                else:
                    # screenshot missing
                    screenshots[varname] = []

        self.NOSHOT = self._get_or_set_noshot_url()
        for val in screenshots:
            if screenshots[val] == []:
                screenshots[val].append(self.NOSHOT)

        return screenshots, longnames, manytype

    def all_tests(self, batch):
        # Only cache chronological data once
        if "chronological" not in self.alltests_cache:
            # Process the base chronological data once
            import logging
            from concurrent.futures import ThreadPoolExecutor
            import threading

            logger = logging.getLogger(__name__)
            logger.info(
                f"Building chronological data - will be used for both chronological and reverse"
            )

            # Process test directories in parallel for much better performance
            logger.info("Starting parallel processing of test directories...")
            time_dict = {}

            try:
                # Use glob instead of walk to avoid potential hanging issues
                import os

                logger.info("Getting test directories with glob...")
                test_dirs = glob(join("static", "report", "*"))
                logger.info(f"Glob returned {len(test_dirs)} items")
                test_list = [d.split("/")[-1] for d in test_dirs if os.path.isdir(d)]
                logger.info(f"Found {len(test_list)} test directories to process")
            except Exception as e:
                logger.error(f"Error getting test list: {e}")
                return []

            def process_single_test(testname):
                try:
                    m = join("static", "report", testname, "meta.csv")
                    with open(m, "r") as fin:
                        reader = csv.DictReader(fin)
                        r = next(reader)
                        time = int(r["time"])
                        return time, testname
                except Exception as e:
                    logger.debug(f"Error processing test {testname}: {e}")
                    return None

            # Process tests in parallel with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(process_single_test, testname)
                    for testname in test_list
                ]

                # Collect all results first, then process them in order
                results = []
                completed = 0
                for future in futures:
                    try:
                        result = future.result(timeout=5)  # 5 second timeout per test
                        if result:
                            results.append(result)
                        completed += 1
                        if completed % 50 == 0:
                            logger.info(
                                f"Processed {completed}/{len(test_list)} test directories"
                            )
                    except Exception as e:
                        logger.error(f"Error in parallel processing: {e}")
                        completed += 1

                # Now process results in chronological order
                logger.info("Sorting results chronologically...")
                results.sort(key=lambda x: x[0])  # Sort by timestamp

                # Build time_dict with proper ordering
                for time, testname in results:
                    # Handle time collisions
                    while time in time_dict and time_dict[time] != testname:
                        time += 1
                    time_dict[time] = testname

            logger.info(
                f"Successfully processed {len(time_dict)} tests with valid meta.csv files"
            )
            if len(time_dict) == 0:
                logger.error("No tests were processed successfully")
                return []

            logger.info("Building chronological batch...")
            sorted_timekey_list = sorted(time_dict)
            self.alltests_cache["chronological"] = []
            for time in sorted_timekey_list:
                self.alltests_cache["chronological"].append(time_dict[time])
            logger.info(
                f"Built chronological batch with {len(self.alltests_cache['chronological'])} tests"
            )

        # Now return the appropriate batch
        if batch == "chronological":
            return self.alltests_cache["chronological"]
        elif batch == "reverse":
            # Just return chronological data in reverse order
            return list(reversed(self.alltests_cache["chronological"]))
        else:
            # Handle other batch types (random, ascending, descending, etc.)
            if batch == "random" and batch not in self.alltests_cache:
                test_list = next(walk(join("static", "report")))[1]
                shuffle(test_list)
                self.alltests_cache[batch] = test_list

            elif (
                batch in ["ascending", "descending"]
                and batch not in self.alltests_cache
            ):
                metas = glob(join("static", "report", "*", "meta.csv"))
                tests = dict()
                final_list = []

                for m in metas:
                    try:
                        with open(m, "r") as fin:
                            testname = m[14:-9]
                            # after static/report/ and before meta.csv"
                            reader = csv.DictReader(fin)
                            r = next(reader)
                            guess = float(r["bestguess"])
                            inserted_yet = False
                            while not inserted_yet:
                                if guess in tests and tests[guess] != testname:
                                    guess += 0.001
                                else:
                                    tests[guess] = testname
                                    inserted_yet = True
                    except FileNotFoundError:
                        continue

                sorted_tests = sorted(tests)
                for guess in sorted_tests:
                    final_list.append(tests[guess])

                ascending = final_list[:]
                final_list.reverse()
                descending = final_list[:]
                self.alltests_cache["descending"] = descending
                self.alltests_cache["ascending"] = ascending

            elif batch in ["english", "foreign"] and batch not in self.alltests_cache:
                english_test_list = []
                foreign_gibberish = []
                chron = self.all_tests("chronological")

                for testname in chron:
                    m = join("static", "report", testname, "meta.csv")
                    try:
                        with open(m, "r") as fin:
                            reader = csv.DictReader(fin)
                            r = next(reader)
                            lang = r["language"].lower()
                            if lang == "yy" or lang == "en":
                                english_test_list.append(testname)
                            else:
                                foreign_gibberish.append(testname)
                    except FileNotFoundError:
                        pass

                self.alltests_cache["english"] = english_test_list
                self.alltests_cache["foreign"] = foreign_gibberish

            elif batch == "interesting" and batch not in self.alltests_cache:
                # Get interesting tests from config instead of hardcoded list
                try:
                    interesting_tests = self.app.config.get("INTERESTING_TESTS", [])
                except AttributeError:
                    # Fallback if config is not available
                    interesting_tests = []

                # Filter to only include tests that actually exist
                existing_tests = []
                for test in interesting_tests:
                    if self.test_in_batch(test, "chronological"):
                        existing_tests.append(test)

                self.alltests_cache["interesting"] = existing_tests

            elif batch not in self.alltests_cache:
                try:
                    test_list = []
                    filename = join("static", "order", batch + ".txt")
                    with open(filename, "r") as fin:
                        for line in fin:
                            test_list.append(line.rstrip())

                    self.alltests_cache[batch] = test_list
                except FileNotFoundError:
                    # Log the error and provide a more descriptive message
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Batch order file not found for '{batch}': {filename}"
                    )
                    self.alltests_cache[batch] = []

        # Return the appropriate batch
        if batch in self.alltests_cache:
            return self.alltests_cache[batch]
        else:
            logger.error(f"Unknown batch type: {batch}")
            return []

    def test_in_batch(self, thistest, batch):
        alltests = self.all_tests(batch)
        if thistest not in alltests:
            return False
        return True

    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    # Called by hello.py

    def first_test(self, batch):
        # Thanks to: http://stackoverflow.com/questions/973473/getting-a-list-of-all-subdirectories-in-the-current-directory
        test_list = self.all_tests(batch)
        # assume all_tests() already sorts
        if not test_list:
            return "error"
        else:
            result = test_list[0]
            return result

    def find_random_test(self, batch):
        possibilities = self.all_tests(batch)
        randtest = choice(possibilities)
        return randtest

    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############

    # PRIVATE:

    def _is_confident(self, winrow):
        lowbound = winrow["lowerbound"]
        if float(lowbound) < 0:  # if there is no clear winner
            return False
        return True

    def _get_row(self, dirname):
        try:
            with open(join(dirname, "meta.csv"), "r") as fin:
                reader = csv.DictReader(fin, delimiter=",")
                row_dict = next(reader)  # skip header
                return row_dict
        except FileNotFoundError:
            return None

    def _true_results(self, winrow, dirname, isconfidence, guess=None):
        winner = winrow["winner"]
        loser = winrow["loser"]
        guessedcorrectly = False
        leancorrectly = False
        if guess is not None:
            if not isconfidence:
                if guess == GUESSNODIFF:
                    guessedcorrectly = True
            else:  # if there is a clear winner
                if guess.lower() == winner.lower():
                    guessedcorrectly = True
            if guess.lower() == winner.lower():
                leancorrectly = True
        else:
            guessedcorrectly = None
            leancorrectly = None

        winner = self._real_value(winner, dirname)  # No need for decode in Python 3
        loser = self._real_value(loser, dirname)  # No need for decode in Python 3
        return guessedcorrectly, leancorrectly, winner, loser

    def _is_url(self, f_or_url):
        isurl = False
        if f_or_url[0:4] == "http":
            isurl = True
        return isurl

    def _exists_url(self, file_or_url):
        # print "does" + file_or_url + "exist?"
        try:
            with urllib.request.urlopen(urllib.request.Request(file_or_url)) as f:
                # print ('yes')
                return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            # print('no')
            return False

    def _exists_file(self, file_or_url):
        try:
            with open(
                file_or_url[1:]
            ):  # because of the weird way self.url_for works (it prefixes a forward slash to "static/...")
                return True
        except IOError:
            return False

    def _exists_and_is_url(self, file_or_url):
        # Given a url or file, try to fetch that item, and return if it exists or not
        is_a_url = self._is_url(file_or_url)

        if is_a_url:
            return self._exists_url(file_or_url), True
        else:
            return self._exists_file(file_or_url), False

    def _max_diagnostic_num(self, testname, diag_type):
        # returns the maximum X on the files called "diagnostic[X].jpeg"
        # assuming that there is no gap
        # return 0 if none exist
        STARTCHECK = 10
        MAXNUM = 30
        # start at i = STARTCHECK. See if there's a plot of the name diagnostic<i>.jpeg existing.
        #   If not, decrement i until it does. (Stop below 1)
        #   If so, increment i until it doesn't (Stop at MAXNUM)
        # return i
        i = STARTCHECK
        direction = "start"
        use_local = False
        while i > 0 and i < MAXNUM:
            if diag_type != "":
                filename = "_".join(["diagnostic", diag_type, str(i)])
            else:
                filename = "_".join(["diagnostic", str(i)])
            file_or_url_name = join("report", testname, filename + ".jpeg")
            exists, isurl = self._exists_and_is_url(
                self.url_for("static", filename=file_or_url_name)
            )
            # if it's not on the server, fallback to trying local file
            if isurl and not exists:
                # print ('isurl and not exists')
                # print ('isurl = '+ str(isurl))
                # print ('exists = '+ str(exists))
                exists, isurl = self._exists_and_is_url(
                    join("/static", file_or_url_name)
                )
                if exists:
                    use_local = True
                # the slash is needed to mimic the bad behavior of self.url_for

            if exists:
                # print(file_or_url_name)
                if direction == "decrement":
                    # print "returning " + str(i) + ","+str(use_local)
                    return i, use_local
                else:
                    i = i + 1
                    direction = "increment"
            else:
                if direction == "increment":
                    # print "returning " + str(i) + ","+str(use_local)
                    return i, use_local
                else:
                    i = i - 1
                    direction = "decrement"
        # print "returning " + str(i) + ","+str(use_local)
        return i, False

    def _real_value(self, value_slug, dirname):
        # given a short value, and the dirname (static/report/testname), look up the long description
        try:
            with open(join(dirname, "val_lookup.csv"), "r") as fin:
                reader = csv.reader(fin, delimiter=",")
                next(reader)  # skip header
                lookup = dict(reader)
                return lookup[value_slug]
        except FileNotFoundError:
            return value_slug

    def _get_or_set_noshot_url(self):
        if not self.NOSHOT:
            self.NOSHOT = self.url_for("static", filename="img/noshot.gif")
            # exists, isurl = exists_and_is_url(self.NOSHOT)
            # if(not exists):
            # 	self.NOSHOT = local_self.url_for('static', filename='img/noshot.gif')
        return self.NOSHOT

    def _get_s3_screenshot_url(self, imgur_url, testname, value):
        """
        Get S3 screenshot URL with fallback logic:
        1. Try screenshotsClean first
        2. Fallback to screenshotsImgur
        3. Final fallback to original imgur URL
        """
        try:
            from urllib.parse import urlparse
            import os

            # Extract imgur filename from URL
            parsed = urlparse(imgur_url)
            imgur_filename = os.path.basename(parsed.path)

            # Try screenshotsClean first (organized structure)
            clean_url = f"https://wikitoy.s3.us-east-1.amazonaws.com/screenshotsClean/{testname}/{value}.png"

            # Check if screenshotsClean exists by making a HEAD request
            if self._check_s3_url_exists(clean_url):
                return clean_url

            # Fallback to screenshotsImgur
            imgur_s3_url = f"https://wikitoy.s3.us-east-1.amazonaws.com/screenshotsImgur/{imgur_filename}"
            if self._check_s3_url_exists(imgur_s3_url):
                return imgur_s3_url

            # Final fallback to original imgur URL
            return imgur_url

        except Exception:
            # Fallback to original imgur URL
            return imgur_url

    def _check_s3_url_exists(self, url):
        """
        Check if an S3 URL exists by making a HEAD request
        """
        try:
            import urllib.request

            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def _get_s3_imgur_fallback_url(self, imgur_url):
        """
        Generate screenshotsImgur fallback URL
        """
        try:
            from urllib.parse import urlparse
            import os

            # Extract imgur filename from URL
            parsed = urlparse(imgur_url)
            imgur_filename = os.path.basename(parsed.path)

            # Generate screenshotsImgur URL
            imgur_s3_url = f"https://wikitoy.s3.us-east-1.amazonaws.com/screenshotsImgur/{imgur_filename}"

            return imgur_s3_url

        except Exception:
            # Fallback to original imgur URL
            return imgur_url

    def _diagnostic_types(self, testname):
        type_re = r"diagnostic_(?P<type>.*)_[0-9]*\.jpeg$"
        files = next(walk(join("static", "report", testname)))[2]
        alltypes = [""]
        for filename in files:
            matches = re.match(type_re, filename)
            if matches:
                diagtype = matches.group("type")
                alltypes.append(diagtype)
        alltypes = list(set(alltypes))
        return alltypes

    #############
    #############
    #############
    #############
    #############
    #############
    #############
    #############
