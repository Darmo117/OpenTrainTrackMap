/**
 * A partial date may represent either a year, a year and month or a year, month and day.
 */
export class PartialDate {
  static readonly #PATTERN = /^(\d{4})-(\d\d|\?\?)-(\d\d|\?\?)$/;

  /**
   * Parse the given string into a {@code PartialDate} object.
   * @param s The string to parse.
   * @returns A new {@code PartialDate} object.
   * @throws {Error} If the string does not represent a valid partial date.
   * @see toString
   */
  static parse(s: string): PartialDate {
    const match = this.#PATTERN.exec(s);
    if (!match) {
      throw new Error(`Invalid partial date string: ${s}`);
    }
    const year = +match.groups[1];
    const month = match.groups[2];
    const day = match.groups[3];
    if (month !== "??") {
      if (day !== "??") {
        return new this(year, +month, +day);
      }
      return new this(year, +month);
    }
    return new this(year);
  }

  /**
   * Return a {@code PartialDate} instance representing the current local date.
   * The month and day or guaranteed to be set.
   */
  static now(): PartialDate {
    const date = new Date();
    return new this(date.getFullYear(), date.getMonth() + 1, date.getDate());
  }

  readonly #year: number;
  readonly #month: number | null;
  readonly #day: number | null;

  /**
   * Create a new partial date.
   * @param year The date’s year. Must be ≥ 0 and ≤ 9999.
   * @param month Optional. The date’s month. Must be between 1 and 12 inclusive.
   * @param day Optional. The month’s day. Must be a valid day for the given month.
   * @throws {Error} If any of the following conditions is true:
   *  - the year is undefined or ≤ 0
   *  - the month is undefined but the day is
   *  - the month is not between 1 and 12 inclusive
   *  - the day is invalid for the given month
   */
  constructor(year: number, month?: number, day?: number) {
    if (typeof year !== "number" || year < 0 || year > 9999) {
      throw new Error(`Invalid year: ${year}`);
    }
    const monthDef = typeof month === "number";
    const dayDef = typeof day === "number";
    if (!monthDef && dayDef) {
      throw new Error("Day cannot be set while month is undefined");
    }
    if (monthDef) {
      if (month < 1 || month > 12) {
        throw new Error(`Invalid month: ${month}`);
      }
      if (dayDef) {
        PartialDate.#checkDate(year, month, day);
      }
    }
    this.#year = year;
    this.#month = month;
    this.#day = day;
  }

  /**
   * Check whether the given year/month/day combination is valid.
   * @throws {Error} If it is not.
   */
  static #checkDate(y: number, m: number, d: number) {
    const leapYear = y % 4 === 0 && y % 100 !== 0 || y % 400 === 0;
    if (d < 1
        || (m === 1 || m === 3 || m === 5 || m === 7 || m === 8 || m === 10 || m === 12) && d > 31
        || (m === 4 || m === 6 || m === 9 || m === 11) && d > 30
        || m === 2 && (leapYear && d > 29 || !leapYear && d > 28)) {
      throw new Error(`Invalid day: ${d}`);
    }
  }

  /**
   * This date’s year.
   */
  get year(): number {
    return this.#year;
  }

  /**
   * This date’s month (between 1 and 12) or null if undefined.
   */
  get month(): number | null {
    return this.#month;
  }

  /**
   * This date’s day of month or null if undefined.
   */
  get day(): number | null {
    return this.#day;
  }

  /**
   * Check whether this date is equal to the given one.
   * @param other A date to check against this one.
   * @returns True if this date is the exact same as the given one.
   */
  equals(other: PartialDate): boolean {
    return this.year === other.year && this.month === other.year && this.day === other.day;
  }

  /**
   * Check whether this date precedes the given one.
   * @param other A date to check against this one.
   * @returns True if this date precedes the given one, false otherwise.
   */
  precedes(other: PartialDate): boolean {
    return this.year < other.year
        || this.year === other.year && (
            (this.month ?? 1) < (other.month ?? 1)
            || (this.month ?? 1) === (other.month ?? 1) && (
                (this.day ?? 1) < (other.day ?? 1)
            )
        );
  }

  /**
   * Check whether this date precedes or equals the given one.
   * @param other A date to check against this one.
   * @returns True if this date precedes or equals the given one, false otherwise.
   */
  precedesOrEquals(other: PartialDate): boolean {
    return this.precedes(other) || this.equals(other);
  }

  /**
   * Check whether this date follows the given one.
   * @param other A date to check against this one.
   * @returns True if this date follows the given one, false otherwise.
   */
  follows(other: PartialDate): boolean {
    return this.year > other.year
        || this.year === other.year && (
            (this.month ?? 1) > (other.month ?? 1)
            || (this.month ?? 1) === (other.month ?? 1) && (
                (this.day ?? 1) > (other.day ?? 1)
            )
        );
  }

  /**
   * Check whether this date follows or equals the given one.
   * @param other A date to check against this one.
   * @returns True if this date follows or equals the given one, false otherwise.
   */
  followsOrEquals(other: PartialDate): boolean {
    return this.follows(other) || this.equals(other);
  }

  /**
   * Convert this date to a string in the format `YYYY-MM-DD`
   * where `MM` and `DD` can be `??` if either of those is undefined.
   */
  toString(): string {
    const year = this.year.toLocaleString("en-US", {minimumSignificantDigits: 4});
    const month = this.month?.toLocaleString("en-US", {minimumSignificantDigits: 2}) ?? "??";
    const day = this.day?.toLocaleString("en-US", {minimumSignificantDigits: 2}) ?? "??";
    return `${year}-${month}-${day}`;
  }
}

/**
 * A date interval represents a period on the timeline between two dates (inclusive).
 * Each boundary date may be set as approximate. If no end date is defined, the property `isCurrent`
 * indicates whether the interval has still not ended at the current time.
 */
export class DateInterval {
  static readonly #PATTERN = /^\[(~?\d{4}(?:-(?:\d\d|\?\?)){2}|\?),\s*(~?\d{4}(?:-(?:\d\d|\?\?)){2}|\?|\.{3})]$/;

  /**
   * Parse the given string into a {@code DateInterval} object.
   * @param s The string to parse.
   * @returns A new {@code DateInterval} object.
   * @throws {Error} If the string does not represent a valid date interval.
   * @see toString
   */
  static parse(s: string): DateInterval {
    const m = this.#PATTERN.exec(s);
    if (!m) {
      throw new Error(`Invalid date interval string: ${s}`);
    }
    const [approxStart, startDate] = this.#extractDatetime(m, 1);
    if (m.groups[2] === "...") {
      return new this(startDate, null, approxStart, false, true);
    }
    const [approxEnd, endDate] = this.#extractDatetime(m, 2);
    return new this(startDate, endDate, approxStart, approxEnd);
  }

  /**
   * Parse the date at the given index in the match object’s groups.
   * @param match The RegExp match object.
   * @param index The index in the match object’s groups.
   * @return A tuple with a boolean indicating whether the date is defined (`true`) or not (`?`),
   *  and the corresponding {@link PartialDate} object.
   */
  static #extractDatetime(match: RegExpMatchArray, index: number): [boolean, PartialDate | null] {
    let s = match.groups[index];
    if (s === "?") {
      return [false, null];
    }
    const approx = s.charAt(0) === "~";
    if (approx) {
      s = s.substring(1);
    }
    return [approx, PartialDate.parse(s)];
  }

  readonly #startDate: PartialDate | null;
  readonly #endDate: PartialDate | null;
  readonly #approxStart: boolean;
  readonly #approxEnd: boolean;
  readonly #isCurrent: boolean;

  /**
   * Create a date interval.
   * @param startDate The start date. May be null.
   * @param endDate The end date (inclusive). May be null.
   * @param approxStart Optional. Whether the start date is approximate.
   * @param approxEnd Optional. Whether the end date is approximate.
   * @param isCurrent Optional. Whether the interval is current.
   * @throws {Error} In any of the following cases:
   *  - start and end dates are both undefined
   *  - end date precedes start date
   *  - start date follows end date
   *  - start and end date are equal
   *  - `isCurrent` is true and end date is set
   *  - `approxStart` is true and start date is undefined
   *  - `approxEnd` is true and end date is undefined
   */
  constructor(
      startDate: PartialDate | null,
      endDate: PartialDate | null,
      approxStart: boolean = false,
      approxEnd: boolean = false,
      isCurrent: boolean = false
  ) {
    if (!startDate && !endDate) {
      throw new Error("startDate and endDate cannot be both null")
    }
    if (endDate) {
      if (startDate) {
        if (endDate.equals(startDate)) {
          throw new Error("startDate and endDate must be different");
        }
        if (endDate.precedes(startDate)) {
          throw new Error("attempt to set startDate after endDate");
        }
        if (startDate.follows(endDate)) {
          throw new Error("attempt to set endDate before startDate");
        }
      }
      if (isCurrent) {
        throw new Error("isCurrent cannot be true while endDate is defined")
      }
    } else if (approxEnd) {
      throw new Error("approxEnd cannot be true while endDate is undefined");
    }
    if (approxStart && !startDate) {
      throw new Error("approxStart cannot be true while startDate is undefined");
    }
    this.#startDate = startDate;
    this.#endDate = endDate;
    this.#approxStart = approxStart;
    this.#approxEnd = approxEnd;
    this.#isCurrent = isCurrent;
  }

  /**
   * This interval’s start date or null if it is undefined.
   */
  get startDate(): PartialDate | null {
    return this.#startDate;
  }

  /**
   * This interval’s end date or null if it is undefined.
   */
  get endDate(): PartialDate | null {
    return this.#endDate;
  }

  /**
   * Indicates whether this interval’s start date is approximate.
   */
  get hasApproxStartDate(): boolean {
    return this.#approxStart;
  }

  /**
   * Indicates whether this interval’s end date is approximate.
   */
  get hasApproxEndDate(): boolean {
    return this.#approxEnd;
  }

  /**
   * Indicates whether this interval is still current.
   */
  get isCurrent(): boolean {
    return this.#isCurrent;
  }

  /**
   * Check whether this interval is the exact same as the given one.
   * @param other An interval to check against this one.
   * @returns True if both intervals are equal, false otherwise.
   */
  equals(other: DateInterval): boolean {
    return this.hasApproxStartDate === other.hasApproxStartDate
        && this.hasApproxEndDate === other.hasApproxEndDate
        && this.startDate.equals(other.startDate)
        && this.endDate.equals(other.endDate)
        && this.isCurrent === other.isCurrent;
  }

  /**
   * Check whether this interval precedes the given one, with a gap in-between.
   * @param other An interval to check against this one.
   * @returns True if this interval’s end date precedes the start date of the given one,
   *  false otherwise.
   */
  precedes(other: DateInterval): boolean {
    return this.endDate && other.startDate && this.endDate.precedes(other.startDate);
  }

  /**
   * Check whether this interval precedes the given one, with no gap in-between.
   * @param other An interval to check against this one.
   * @returns True if this interval’s end date is the same as the start date of the given one,
   *  false otherwise.
   */
  precedesAndMeets(other: DateInterval): boolean {
    return this.endDate && other.startDate && this.endDate.equals(other.startDate);
  }

  /**
   * Check whether this interval follows the given one, with a gap in-between.
   * @param other An interval to check against this one.
   * @returns True if this interval’s start date follows the end date of the given one,
   *  false otherwise.
   */
  follows(other: DateInterval): boolean {
    return this.startDate && other.endDate && this.startDate.follows(other.endDate);
  }

  /**
   * Check whether this interval follows the given one, with no gap in-between.
   * @param other An interval to check against this one.
   * @returns True if this interval’s start date is the same as the end date of the given one,
   *  false otherwise.
   */
  followsAndMeets(other: DateInterval): boolean {
    return this.startDate && other.endDate && this.startDate.equals(other.endDate);
  }

  /**
   * Check whether this interval overlaps the given one.
   * @param other An interval to check against this one.
   * @returns True if this interval starts inside the given one,
   *  or the given one starts inside this one,
   *  or this start date is the given one’s end date,
   *  or this end date is the given one’s start date; false otherwise.
   */
  overlaps(other: DateInterval): boolean {
    const now = PartialDate.now();
    const thisEnd = this.isCurrent ? now : this.endDate;
    const otherEnd = other.isCurrent ? now : other.endDate;
    return (
        this.startDate && thisEnd && ( // Other starts or ends inside this
            other.startDate && this.startDate.precedesOrEquals(other.startDate) && other.startDate.precedesOrEquals(thisEnd)
            || otherEnd && this.startDate.precedesOrEquals(otherEnd) && otherEnd.precedesOrEquals(this.endDate)
        )
    ) || (
        other.startDate && otherEnd && ( // This starts or ends inside other
            this.startDate && other.startDate.precedesOrEquals(this.startDate) && this.startDate.precedesOrEquals(otherEnd)
            || thisEnd && other.startDate.precedesOrEquals(thisEnd) && thisEnd.precedesOrEquals(otherEnd)
        )
    );
  }

  /**
   * Convert this date interval to a string in the format `[~?<partial date>, ~?<partial date>]`
   * where `<partial date>` is a serialized {@link PartialDate} object and `~` indicates that the following date
   * is approximate. The first date is the start date, the second is the end date.
   *
   * If a date is unknown, it is replaced by a single `?`.
   *
   * If the end date is undefined and the `isCurrent` flag is `true`,
   * the second date is replaced by three dots (`...`).
   * @see PartialDate.toString
   */
  toString(): string {
    let start = this.startDate?.toString() ?? "?";
    if (this.startDate && this.hasApproxStartDate) {
      start = "~" + start;
    }
    let end: string;
    if (this.isCurrent) {
      end = "...";
    } else {
      end = this.endDate?.toString() ?? "?";
      if (this.endDate && this.hasApproxEndDate && !this.isCurrent) {
        end = "~" + end;
      }
    }
    return `[${start}, ${end}]`;
  }
}
