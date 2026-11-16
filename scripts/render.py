#!/usr/bin/env python3
"""Render data/profile.yaml into build/resume.tex and build/profile.json.

Usage:
    python scripts/render.py                    # public build, variant "default"
    python scripts/render.py --variant ml       # items tagged "ml" join the default set
    RESUME_PHONE="..." python scripts/render.py --out build/private
                                                # private build with a phone line

The phone number never lives in data/profile.yaml and never reaches
profile.json. It only enters the .tex when RESUME_PHONE is set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "profile.yaml"
TEMPLATES = ROOT / "templates"
DEFAULT_OUT = ROOT / "build"
DEFAULT_VARIANT = "default"

EM_DASH = "\u2014"
EN_DASH = "\u2013"
# North American phone shapes: three digits, three digits, four digits,
# separated by a dash, dot or space, with optional parentheses and +1.
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
PHONE_CHARS_RE = re.compile(r"^[0-9+()\s.-]{7,20}$")

TEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
    "|": r"\textbar{}",
    EN_DASH: "--",
    "\u2018": "`",
    "\u2019": "'",
    "\u201c": "``",
    "\u201d": "''",
    "\u00a0": "~",
}
# An abbreviation followed by a space must not get sentence spacing.
ABBREV_RE = re.compile(r"\b(vs|etc|e\.g|i\.e|approx)\. ")


class ProfileError(ValueError):
    """The profile data breaks a rule of the public file."""


def tex_escape(value: object) -> str:
    text = str(value)
    if EM_DASH in text:
        raise ProfileError(f"em dash (U+2014) in {text!r}; use a comma, colon or parentheses")
    out = "".join(TEX_SPECIALS.get(ch, ch) for ch in text)
    out = ABBREV_RE.sub(lambda m: m.group(1) + ".\\ ", out)
    bad = sorted({ch for ch in out if ord(ch) > 127})
    if bad:
        raise ProfileError(
            f"non-ASCII characters {bad!r} in {text!r}; add them to TEX_SPECIALS or rewrite"
        )
    return out


def finalize(value: object) -> object:
    """Escape every rendered variable unless a filter already marked it safe."""
    if isinstance(value, Markup):
        return value
    if value is None:
        return ""
    return tex_escape(value)


def url_filter(value: object) -> Markup:
    text = str(value)
    if "\\" in text or any(ch.isspace() for ch in text):
        raise ProfileError(f"unsupported character in URL {text!r}")
    return Markup(text.replace("%", r"\%").replace("#", r"\#"))


def parens_filter(value: object) -> str:
    return f"({value})"


def daterange_filter(item: dict) -> str:
    start = str(item.get("start", "")).strip()
    end = str(item.get("end", "")).strip()
    if start and end and start != end:
        return f"{start} {EN_DASH} {end}"
    return start or end


def roles_filter(roles: list) -> str:
    parts = []
    for role in roles:
        dates = daterange_filter(role)
        parts.append(f"{role['title']} ({dates})" if dates else role["title"])
    return ", ".join(parts)


def walk_strings(node, path="profile"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from walk_strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def walk_keys(node, path="profile"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}", key
            yield from walk_keys(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from walk_keys(value, f"{path}[{i}]")


def validate(profile: dict) -> None:
    """Public-file rules: no phone, no em dash, the fields the template needs."""
    for path, key in walk_keys(profile):
        if str(key).lower() in {"phone", "telephone", "mobile", "tel"}:
            raise ProfileError(f"{path}: the public file must not hold a phone field; use RESUME_PHONE")
    for path, text in walk_strings(profile):
        if PHONE_RE.search(text):
            raise ProfileError(f"{path}: looks like a phone number; keep it out of the public file")
        if EM_DASH in text:
            raise ProfileError(f"{path}: em dash (U+2014); use a comma, colon or parentheses")
    for field in ("name", "summary", "contact", "links"):
        if not profile.get(field):
            raise ProfileError(f"profile.{field} is required")
    if not profile["contact"].get("email"):
        raise ProfileError("profile.contact.email is required")


def select_variant(node, variant: str):
    """Drop list items whose `variants` tags do not include `variant`."""
    if isinstance(node, dict):
        return {k: select_variant(v, variant) for k, v in node.items() if k != "variants"}
    if isinstance(node, list):
        kept = []
        for item in node:
            if isinstance(item, dict) and item.get("variants"):
                if variant not in item["variants"]:
                    continue
            kept.append(select_variant(item, variant))
        return kept
    return node


def read_phone() -> str | None:
    phone = os.environ.get("RESUME_PHONE", "").strip()
    if not phone:
        return None
    if not PHONE_CHARS_RE.match(phone):
        raise ProfileError("RESUME_PHONE holds characters other than digits, spaces, + ( ) . -")
    return phone


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((=",
        comment_end_string="=))",
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
        undefined=StrictUndefined,
        finalize=finalize,
    )
    env.filters["url"] = url_filter
    env.filters["parens"] = parens_filter
    env.filters["daterange"] = daterange_filter
    env.filters["roles"] = roles_filter
    return env


class _Attr(dict):
    """Dict with attribute access that returns None for missing optional keys."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None


def attrify(node):
    if isinstance(node, dict):
        return _Attr({k: attrify(v) for k, v in node.items()})
    if isinstance(node, list):
        return [attrify(v) for v in node]
    return node


def render(data_path: Path, out_dir: Path, variant: str) -> tuple[Path, Path]:
    profile = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ProfileError(f"{data_path} is not a mapping")
    validate(profile)
    phone = read_phone()

    selected = attrify(select_variant(profile, variant))
    tex = build_env().get_template("resume.tex.j2").render(p=selected, phone=phone, variant=variant)
    if EM_DASH in tex:
        raise ProfileError("rendered .tex contains an em dash")
    if phone is None and PHONE_RE.search(tex):
        raise ProfileError("rendered .tex contains a phone number although RESUME_PHONE is unset")

    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "resume.tex"
    json_path = out_dir / "profile.json"
    tex_path.write_text(tex, encoding="utf-8")
    # profile.json is the full public file with variant tags kept, so each
    # consumer can pick its own subset. It never carries the phone.
    json_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return tex_path, json_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="profile YAML (default: data/profile.yaml)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory (default: build/)")
    parser.add_argument("--variant", default=DEFAULT_VARIANT, help="variant tag to include (default: default)")
    args = parser.parse_args(argv)
    try:
        tex_path, json_path = render(args.data, args.out, args.variant)
    except ProfileError as err:
        print(f"render.py: {err}", file=sys.stderr)
        return 1
    print(f"wrote {tex_path.relative_to(ROOT) if tex_path.is_relative_to(ROOT) else tex_path}")
    print(f"wrote {json_path.relative_to(ROOT) if json_path.is_relative_to(ROOT) else json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
