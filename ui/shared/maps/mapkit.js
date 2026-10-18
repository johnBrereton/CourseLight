/*!
 * @apple/mapkit-loader — Copyright © 2026 Apple Inc.
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the “Software”), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
import { load } from "@apple/mapkit-loader";

export const loadMaps = (token) => load({ token, version: "6", language: "en-US", libraries: ["full-map", "services"] });

export function withTimeout(promise, milliseconds = 15000) {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error("Apple Maps timed out")), milliseconds);
  })]).finally(() => clearTimeout(timer));
}

export async function locate(api, place, signal) {
  if (place.coordinate) return new api.Coordinate(place.coordinate.latitude, place.coordinate.longitude);
  const response = await withTimeout(new api.Search().search(`${place.name} Lehigh University`, {
    signal, includeAddresses: false, includePhysicalFeatures: false, includePointsOfInterest: true, limitToCountries: "US",
  }));
  const words = place.name.toLowerCase().match(/[a-z]+/g)?.filter(word => !["lehigh", "university", "hall", "building", "center", "laboratory", "lab", "the", "of", "and"].includes(word)) || [];
  const matches = response.places.filter(result => {
    const name = result.name?.toLowerCase() || "";
    return words.length && words.every(word => name.includes(word)) && /bethlehem/i.test(result.formattedAddress || "");
  });
  // A campus-wide or ambiguous search result is not a verified class building.
  if (matches.length !== 1) return null;
  return matches[0].coordinate;
}
