/**
 * Minimal TypeScript declarations for jalaali-js.
 * The library has no official @types package; we only declare the few
 * functions our code calls.
 */
declare module "jalaali-js" {
  export interface JalaaliDate {
    jy: number;
    jm: number;
    jd: number;
  }

  export interface GregorianDate {
    gy: number;
    gm: number;
    gd: number;
  }

  /** Convert a Gregorian date (or JS Date) to a Jalali year/month/day. */
  export function toJalaali(date: Date): JalaaliDate;
  export function toJalaali(gy: number, gm: number, gd: number): JalaaliDate;

  /** Convert a Jalali year/month/day to a Gregorian year/month/day. */
  export function toGregorian(
    jy: number,
    jm: number,
    jd: number
  ): GregorianDate;

  export function isValidJalaaliDate(
    jy: number,
    jm: number,
    jd: number
  ): boolean;
  export function isLeapJalaaliYear(jy: number): boolean;
  export function jalaaliMonthLength(jy: number, jm: number): number;

  const _default: {
    toJalaali: typeof toJalaali;
    toGregorian: typeof toGregorian;
    isValidJalaaliDate: typeof isValidJalaaliDate;
    isLeapJalaaliYear: typeof isLeapJalaaliYear;
    jalaaliMonthLength: typeof jalaaliMonthLength;
  };
  export default _default;
}
