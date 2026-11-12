"""The recipient's local time for the SMS send window, from the phone number's area code.

Quiet hours are the recipient's, not ours: 11:00 Eastern is 05:00 in Honolulu. Each US area code maps to the
zone (or zones) it can be in. A code that straddles two zones lists both, and a code we don't know is treated as
anywhere from Atlantic to Pacific time, so a text only goes out when the window is open in every zone the
number could be in. Being wrong in the safe direction costs a few hours of sending; the other direction is a
text at 6 a.m.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

ET, CT, MT, PT = "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"
AZ, AK, HI, PR = "America/Phoenix", "America/Anchorage", "Pacific/Honolulu", "America/Puerto_Rico"
UNKNOWN = ("America/Halifax", PT)  # the widest continental span: the window must be open from Atlantic to Pacific

_ZONES: dict[tuple[str, ...], str] = {
    (ET,): "201 202 203 207 212 215 216 220 223 227 229 231 234 239 240 248 252 260 267 269 272 276 283 301 302 "
           "304 305 313 315 317 321 324 326 329 330 332 336 339 347 351 352 363 380 386 401 404 407 410 412 413 "
           "419 434 436 440 443 445 463 470 475 478 484 502 508 513 516 517 518 540 551 561 567 570 571 582 585 "
           "586 603 607 609 610 614 616 617 631 640 645 646 656 667 678 679 680 681 689 703 704 706 716 717 718 "
           "724 727 728 732 734 740 743 754 757 762 765 770 771 772 774 781 786 802 803 804 810 813 814 826 828 "
           "835 838 839 843 845 848 854 856 857 859 860 862 863 864 865 878 904 908 910 912 914 917 919 929 934 "
           "937 941 943 947 948 954 959 973 978 980 984 989",
    (CT,): "205 210 214 217 218 224 225 228 251 254 256 262 274 281 309 312 314 316 318 319 320 325 327 331 334 "
           "337 346 361 402 405 409 414 417 430 447 464 469 479 501 504 507 512 515 531 534 539 557 563 572 573 "
           "580 601 608 612 615 618 629 630 636 641 651 659 660 662 682 708 712 713 715 726 730 731 737 763 769 "
           "773 779 806 815 816 817 830 832 847 861 870 872 901 903 913 918 920 936 938 940 945 952 956 972 975 "
           "979 985",
    (MT,): "303 307 385 406 435 505 575 719 720 801 915 970 983",
    (AZ,): "480 520 602 623 928",
    (PT,): "206 209 213 253 279 310 323 341 350 360 369 408 415 424 425 442 503 509 510 530 559 562 564 619 626 "
           "628 650 657 661 669 702 707 714 725 747 760 805 818 820 831 840 858 909 916 925 949 951 971",
    (AK, "America/Adak"): "907",
    (HI,): "808",
    (PR,): "787 939",
    # Area codes that cross a time-zone line: the window has to be open on both sides.
    (ET, CT): "219 270 364 423 448 574 606 812 850 906 930 931",
    (CT, MT): "308 432 605 620 701 785",
    (MT, PT): "208 458 541 775 986",
}
AREA_ZONES: dict[str, tuple[str, ...]] = {code: zones for zones, codes in _ZONES.items() for code in codes.split()}


def area_code(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[:3] if len(digits) == 10 else ""


def zones_for(phone: str) -> tuple[str, ...]:
    return AREA_ZONES.get(area_code(phone), UNKNOWN)


def in_window(phone: str, now: datetime, start_hour: int, end_hour: int) -> bool:
    """True when it is between start_hour and end_hour (local) everywhere the number could be."""
    return all(start_hour <= now.astimezone(ZoneInfo(z)).hour < end_hour for z in zones_for(phone))
