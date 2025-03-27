# npass_service.py
"""
NPASS Service - A Python interface for accessing the NPASS database.

This module provides functions to search for natural products, organisms, and targets
in the NPASS (Natural Product Activity & Species Source) database.
"""

import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sys
import json


class NPASSService:
    """Service for interacting with the NPASS database."""

    BASE_URL = "http://bidd2.nus.edu.sg/NPASS/"
    SEARCH_URL = BASE_URL + "search_np.php"
    SPECIES_SEARCH_URL = BASE_URL + "search_species.php"
    TARGET_SEARCH_URL = BASE_URL + "search_target.php"

    def __init__(self, timeout=10, debug=False):
        """
        Initialize the NPASS service.

        Args:
            timeout (int): Request timeout in seconds
            debug (bool): Enable debug mode
        """
        self.session = requests.Session()
        self.timeout = timeout
        self.debug = debug

        # Setting a user agent to mimic a browser
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def _debug_log(self, message):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")

    def search_molecule(self, molecule_name):
        """
        Search for a natural product molecule by name.

        Args:
            molecule_name (str): The name of the molecule to search for.

        Returns:
            dict: Results of the search.
        """
        print(f"Searching for molecule: {molecule_name}")
        payload = {
            "searchtype": "quickname",
            "quickname": molecule_name,
            "submitbutton": "Search",
        }

        try:
            self._debug_log(f"Sending POST request to {self.SEARCH_URL}")
            response = self.session.post(
                self.SEARCH_URL, data=payload, timeout=self.timeout
            )
            self._debug_log(f"Response status code: {response.status_code}")
            response.raise_for_status()

            # Save response for debugging if needed
            if self.debug:
                with open("molecule_search_response.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                self._debug_log("Saved response to molecule_search_response.html")

            # Parse the HTML response
            self._debug_log("Parsing HTML response")
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract search results
            results = self._parse_molecule_results(soup)
            self._debug_log(f"Found {len(results)} molecule results")

            return {
                "query": molecule_name,
                "type": "molecule",
                "results": results,
                "status": "success" if results else "no_results",
            }

        except requests.Timeout:
            print(f"Request timed out after {self.timeout} seconds")
            return {
                "query": molecule_name,
                "type": "molecule",
                "results": [],
                "status": "timeout",
            }
        except requests.RequestException as e:
            print(f"Error searching for molecule: {e}")
            return {
                "query": molecule_name,
                "type": "molecule",
                "results": [],
                "status": "error",
                "error": str(e),
            }

    def search_organism(self, organism_name):
        """
        Search for an organism by name.

        Args:
            organism_name (str): The name of the organism to search for.

        Returns:
            dict: Results of the search.
        """
        print(f"Searching for organism: {organism_name}")
        payload = {
            "searchtype": "quickname",
            "quickname": organism_name,
            "submitbutton": "Search",
        }

        try:
            self._debug_log(f"Sending POST request to {self.SPECIES_SEARCH_URL}")
            response = self.session.post(
                self.SPECIES_SEARCH_URL, data=payload, timeout=self.timeout
            )
            self._debug_log(f"Response status code: {response.status_code}")
            response.raise_for_status()

            # Save response for debugging if needed
            if self.debug:
                with open("organism_search_response.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                self._debug_log("Saved response to organism_search_response.html")

            # Parse the HTML response
            self._debug_log("Parsing HTML response")
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract search results
            results = self._parse_organism_results(soup)
            self._debug_log(f"Found {len(results)} organism results")

            return {
                "query": organism_name,
                "type": "organism",
                "status": "success" if results else "no_results",
                "results": results,
            }

        except requests.Timeout:
            print(f"Request timed out after {self.timeout} seconds")
            return {
                "query": organism_name,
                "type": "organism",
                "results": [],
                "status": "timeout",
            }
        except requests.RequestException as e:
            print(f"Error searching for organism: {e}")
            return {
                "query": organism_name,
                "type": "organism",
                "results": [],
                "status": "error",
                "error": str(e),
            }

    def search_target(self, target_name):
        """
        Search for a target by name.

        Args:
            target_name (str): The name of the target to search for.

        Returns:
            dict: Results of the search.
        """
        print(f"Searching for target: {target_name}")
        payload = {
            "searchtype": "quickname",
            "quickname": target_name,
            "submitbutton": "Search",
        }

        try:
            self._debug_log(f"Sending POST request to {self.TARGET_SEARCH_URL}")
            response = self.session.post(
                self.TARGET_SEARCH_URL, data=payload, timeout=self.timeout
            )
            self._debug_log(f"Response status code: {response.status_code}")
            response.raise_for_status()

            # Save response for debugging if needed
            if self.debug:
                with open("target_search_response.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                self._debug_log("Saved response to target_search_response.html")

            # Parse the HTML response
            self._debug_log("Parsing HTML response")
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract search results
            results = self._parse_target_results(soup)
            self._debug_log(f"Found {len(results)} target results")

            return {
                "query": target_name,
                "type": "target",
                "results": results,
                "status": "success" if results else "no_results",
            }

        except requests.Timeout:
            print(f"Request timed out after {self.timeout} seconds")
            return {
                "query": target_name,
                "type": "target",
                "results": [],
                "status": "timeout",
            }
        except requests.RequestException as e:
            print(f"Error searching for target: {e}")
            return {
                "query": target_name,
                "type": "target",
                "results": [],
                "status": "error",
                "error": str(e),
            }

    def _parse_molecule_results(self, soup):
        """Parse the HTML to extract molecule search results."""
        # This is a simplistic parsing based on the expected HTML structure
        # Will need adjustment based on actual HTML response
        results = []

        try:
            # Look for result tables
            self._debug_log("Looking for molecule results table")
            table = soup.find("table", {"class": "datatable"})
            if not table:
                self._debug_log("No datatable found")
                # Try other potential table classes or IDs
                table = soup.find("table", {"id": "resultstable"})
                if not table:
                    self._debug_log("No resultstable found either")
                    # Just get the first table as a fallback
                    table = soup.find("table")
                    if not table:
                        self._debug_log("No tables found in the response")
                        return results

            # Extract rows from table
            rows = table.find_all("tr")
            self._debug_log(f"Found {len(rows)} rows in the table")
            if len(rows) <= 1:  # Only header row means no results
                return results

            # Skip header row and process data rows
            for row in rows[1:]:
                cells = row.find_all("td")
                if (
                    len(cells) >= 2
                ):  # Ensure we have enough cells for at least ID and Name
                    molecule_id = cells[0].text.strip()
                    molecule_name = (
                        cells[1].text.strip() if len(cells) > 1 else "Unknown"
                    )
                    # Extract link to molecule details
                    link = cells[0].find("a")
                    molecule_url = link["href"] if link else None

                    # Add more fields if available
                    molecule_data = {
                        "id": molecule_id,
                        "name": molecule_name,
                        "url": self.BASE_URL + molecule_url if molecule_url else None,
                    }

                    # Add SMILES or formula if available
                    if len(cells) > 2:
                        molecule_data["additional_info"] = cells[2].text.strip()

                    results.append(molecule_data)

        except Exception as e:
            self._debug_log(f"Error parsing molecule results: {e}")

        return results

    def _parse_organism_results(self, soup):
        """Parse the HTML to extract organism search results."""
        # Similar structure to molecule results parsing
        results = []

        try:
            # Look for result tables
            self._debug_log("Looking for organism results table")
            table = soup.find("table", {"class": "datatable"})
            if not table:
                self._debug_log("No datatable found")
                # Try other potential table classes or IDs
                table = soup.find("table", {"id": "resultstable"})
                if not table:
                    self._debug_log("No resultstable found either")
                    # Just get the first table as a fallback
                    table = soup.find("table")
                    if not table:
                        self._debug_log("No tables found in the response")
                        return results

            # Extract rows from table
            rows = table.find_all("tr")
            self._debug_log(f"Found {len(rows)} rows in the table")
            if len(rows) <= 1:  # Only header row means no results
                return results

            # Skip header row and process data rows
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) >= 2:  # Ensure we have enough cells for ID and Name
                    organism_id = cells[0].text.strip()
                    organism_name = cells[1].text.strip()
                    # Extract link to organism details
                    link = cells[0].find("a")
                    organism_url = link["href"] if link else None

                    results.append(
                        {
                            "id": organism_id,
                            "name": organism_name,
                            "url": (
                                self.BASE_URL + organism_url if organism_url else None
                            ),
                        }
                    )

        except Exception as e:
            self._debug_log(f"Error parsing organism results: {e}")

        return results

    def _parse_target_results(self, soup):
        """Parse the HTML to extract target search results."""
        # Similar structure to other results parsing
        # Look for result tables
        table = soup.find("table", {"class": "datatable"})
        if not table:
            return results

        # Extract rows from table
        rows = table.find_all("tr")
        if len(rows) <= 1:  # Only header row means no results
            return results

        # Skip header row and process data rows
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) >= 2:  # Ensure we have enough cells for ID and Name
                organism_id = cells[0].text.strip()
                organism_name = cells[1].text.strip()
                # Extract link to organism details
                link = cells[0].find("a")
                organism_url = link["href"] if link else None

                results.append(
                    {
                        "id": organism_id,
                        "name": organism_name,
                        "url": self.BASE_URL + organism_url if organism_url else None,
                    }
                )

        return results

    def _parse_target_results(self, soup):
        """Parse the HTML to extract target search results."""
        # Similar structure to other results parsing
        results = []

        # Look for result tables
        table = soup.find("table", {"class": "datatable"})
        if not table:
            return results

        # Extract rows from table
        rows = table.find_all("tr")
        if len(rows) <= 1:  # Only header row means no results
            return results

        # Skip header row and process data rows
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) >= 2:  # Ensure we have enough cells for ID and Name
                target_id = cells[0].text.strip()
                target_name = cells[1].text.strip()
                # Extract link to target details
                link = cells[0].find("a")
                target_url = link["href"] if link else None

                results.append(
                    {
                        "id": target_id,
                        "name": target_name,
                        "url": self.BASE_URL + target_url if target_url else None,
                    }
                )

        return results

    def get_molecule_details(self, molecule_id):
        """
        Get detailed information for a specific molecule.

        Args:
            molecule_id (str): The NPASS ID of the molecule.

        Returns:
            dict: Detailed information about the molecule.
        """
        detail_url = f"{self.BASE_URL}npdetails.php?npid={molecule_id}"

        try:
            response = self.session.get(detail_url)
            response.raise_for_status()

            # Parse the HTML response
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract detailed information (structure depends on the HTML structure)
            details = self._parse_molecule_details(soup, molecule_id)

            return details

        except requests.RequestException as e:
            print(f"Error getting molecule details: {e}")
            return {"id": molecule_id, "status": "error", "error": str(e)}

    def _parse_molecule_details(self, soup, molecule_id):
        """Parse the HTML to extract detailed molecule information."""
        # This needs to be customized based on the actual HTML structure
        details = {"id": molecule_id, "status": "success"}

        # Extract basic information
        try:
            # Name
            name_header = soup.find("h2", {"class": "page-header"})
            if name_header:
                details["name"] = name_header.text.strip()

            # Properties table
            properties_div = soup.find("div", {"id": "properties"})
            if properties_div:
                property_table = properties_div.find("table")
                if property_table:
                    for row in property_table.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            key = (
                                cells[0]
                                .text.strip()
                                .lower()
                                .replace(" ", "_")
                                .replace(":", "")
                            )
                            value = cells[1].text.strip()
                            details[key] = value

            # Activities
            activities_div = soup.find("div", {"id": "activities"})
            if activities_div:
                activities = []
                activity_table = activities_div.find("table")
                if activity_table:
                    for row in activity_table.find_all("tr")[1:]:  # Skip header row
                        cells = row.find_all("td")
                        if len(cells) >= 5:
                            activity = {
                                "target": cells[0].text.strip(),
                                "activity_type": cells[1].text.strip(),
                                "value": cells[2].text.strip(),
                                "unit": cells[3].text.strip(),
                                "reference": cells[4].text.strip(),
                            }
                            activities.append(activity)
                details["activities"] = activities

            # Species sources
            sources_div = soup.find("div", {"id": "sources"})
            if sources_div:
                sources = []
                source_table = sources_div.find("table")
                if source_table:
                    for row in source_table.find_all("tr")[1:]:  # Skip header row
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            source = {
                                "species": cells[0].text.strip(),
                                "taxonomy": (
                                    cells[1].text.strip() if len(cells) > 1 else ""
                                ),
                            }
                            sources.append(source)
                details["sources"] = sources

        except Exception as e:
            print(f"Error parsing molecule details: {e}")
            details["parsing_error"] = str(e)

        return details


def test_service():
    """Test the NPASS service with example queries."""
    service = NPASSService()

    # Test molecule search - Mescaline
    mescaline_results = service.search_molecule("Mescaline")
    print("\nMescaline Search Results:")
    print(f"Status: {mescaline_results['status']}")
    print(f"Found {len(mescaline_results['results'])} results")
    for i, result in enumerate(
        mescaline_results["results"][:5]
    ):  # Show first 5 results
        print(f"{i+1}. {result['name']} (ID: {result['id']})")

    # If we found mescaline, get details
    if mescaline_results["results"]:
        mescaline_id = mescaline_results["results"][0]["id"]
        mescaline_details = service.get_molecule_details(mescaline_id)
        print("\nMescaline Details:")
        if mescaline_details["status"] == "success":
            print(f"Name: {mescaline_details.get('name', 'N/A')}")
            print(
                f"Molecular Formula: {mescaline_details.get('molecular_formula', 'N/A')}"
            )
            print(
                f"Molecular Weight: {mescaline_details.get('molecular_weight', 'N/A')}"
            )

            # Print activities
            activities = mescaline_details.get("activities", [])
            print(f"\nActivities ({len(activities)}):")
            for i, activity in enumerate(activities[:3]):  # Show first 3 activities
                print(
                    f"{i+1}. Target: {activity['target']}, Value: {activity['value']} {activity['unit']}"
                )

            # Print sources
            sources = mescaline_details.get("sources", [])
            print(f"\nSources ({len(sources)}):")
            for i, source in enumerate(sources[:3]):  # Show first 3 sources
                print(f"{i+1}. Species: {source['species']}")

    # Test organism search - Lophophora williamsii
    organism_results = service.search_organism("Lophophora williamsii")
    print("\nLophophora williamsii Search Results:")
    print(f"Status: {organism_results['status']}")
    print(f"Found {len(organism_results['results'])} results")
    for i, result in enumerate(organism_results["results"][:5]):
        print(f"{i+1}. {result['name']} (ID: {result['id']})")

    # Test target search - Serotonin receptor
    target_results = service.search_target("Serotonin receptor")
    print("\nSerotonin (5-HT) receptor Search Results:")
    print(f"Status: {target_results['status']}")
    print(f"Found {len(target_results['results'])} results")
    for i, result in enumerate(target_results["results"][:5]):
        print(f"{i+1}. {result['name']} (ID: {result['id']})")


if __name__ == "__main__":
    test_service()
