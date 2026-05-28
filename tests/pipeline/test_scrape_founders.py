"""Tests for founder scraping — parsing logic only (no network)."""

import pytest
from backend.pipeline.scrape_founders import parse_founders_from_html, strip_s3_signature


def test_strip_s3_signature_removes_query_params():
    url = "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc123.jpg?X-Amz-Algorithm=AWS4&X-Amz-Credential=FAKE"
    result = strip_s3_signature(url)
    assert result == "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc123.jpg"


def test_strip_s3_signature_preserves_clean_url():
    url = "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc123.jpg"
    result = strip_s3_signature(url)
    assert result == url


def test_strip_s3_signature_empty_string():
    assert strip_s3_signature("") == ""


def test_strip_s3_signature_none():
    assert strip_s3_signature(None) is None


SAMPLE_HTML_WITH_FOUNDERS = '''
<html><body>
<div>&quot;company&quot;:{&quot;name&quot;:&quot;TestCo&quot;,&quot;founders&quot;:[{&quot;user_id&quot;:123,&quot;is_active&quot;:true,&quot;full_name&quot;:&quot;Alice Smith&quot;,&quot;title&quot;:&quot;CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc.jpg?X-Amz-Algorithm=AWS4&quot;,&quot;linkedin_url&quot;:&quot;https://linkedin.com/in/alice&quot;,&quot;twitter_url&quot;:&quot;https://twitter.com/alice&quot;,&quot;has_email&quot;:true}],&quot;editUrl&quot;:&quot;https://bookface.ycombinator.com&quot;}</div>
</body></html>
'''


def test_parse_founders_extracts_first_active():
    result = parse_founders_from_html(SAMPLE_HTML_WITH_FOUNDERS)
    assert result is not None
    assert result["founder_name"] == "Alice Smith"
    assert result["founder_title"] == "CEO"
    assert result["founder_avatar_url"] == "https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc.jpg"
    assert result["founder_linkedin"] == "https://linkedin.com/in/alice"
    assert result["founder_twitter"] == "https://twitter.com/alice"


SAMPLE_HTML_NO_FOUNDERS = '''
<html><body>
<div>&quot;company&quot;:{&quot;name&quot;:&quot;EmptyCo&quot;,&quot;founders&quot;:[],&quot;editUrl&quot;:&quot;https://bookface.ycombinator.com&quot;}</div>
</body></html>
'''


def test_parse_founders_returns_none_when_empty():
    result = parse_founders_from_html(SAMPLE_HTML_NO_FOUNDERS)
    assert result is None


def test_parse_founders_returns_none_for_bad_html():
    result = parse_founders_from_html("<html><body>no data here</body></html>")
    assert result is None


SAMPLE_HTML_INACTIVE_FOUNDER = '''
<html><body>
<div>&quot;founders&quot;:[{&quot;user_id&quot;:1,&quot;is_active&quot;:false,&quot;full_name&quot;:&quot;Gone Guy&quot;,&quot;title&quot;:&quot;Ex-CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;&quot;,&quot;linkedin_url&quot;:&quot;&quot;,&quot;twitter_url&quot;:&quot;&quot;,&quot;has_email&quot;:false},{&quot;user_id&quot;:2,&quot;is_active&quot;:true,&quot;full_name&quot;:&quot;Active Alice&quot;,&quot;title&quot;:&quot;CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;https://bookface-images.s3.us-west-2.amazonaws.com/avatars/xyz.jpg&quot;,&quot;linkedin_url&quot;:&quot;https://linkedin.com/in/active&quot;,&quot;twitter_url&quot;:&quot;&quot;,&quot;has_email&quot;:true}],&quot;editUrl&quot;:&quot;x&quot;</div>
</body></html>
'''


def test_parse_founders_skips_inactive():
    result = parse_founders_from_html(SAMPLE_HTML_INACTIVE_FOUNDER)
    assert result is not None
    assert result["founder_name"] == "Active Alice"


def test_parse_founders_extracts_bio_and_has_email():
    result = parse_founders_from_html(SAMPLE_HTML_WITH_FOUNDERS)
    assert result is not None
    assert "founder_bio" in result
    assert "has_email" in result


SAMPLE_HTML_WITH_BIO = '''
<html><body>
<div>&quot;founders&quot;:[{&quot;user_id&quot;:123,&quot;is_active&quot;:true,&quot;founder_bio&quot;:&quot;Alice is a serial entrepreneur who previously founded DataCo.&quot;,&quot;full_name&quot;:&quot;Alice Smith&quot;,&quot;title&quot;:&quot;CEO&quot;,&quot;avatar_thumb_url&quot;:&quot;https://bookface-images.s3.us-west-2.amazonaws.com/avatars/abc.jpg&quot;,&quot;linkedin_url&quot;:&quot;https://linkedin.com/in/alice&quot;,&quot;twitter_url&quot;:&quot;https://twitter.com/alice&quot;,&quot;has_email&quot;:true}],&quot;editUrl&quot;:&quot;x&quot;</div>
</body></html>
'''


def test_parse_founders_extracts_bio_text():
    result = parse_founders_from_html(SAMPLE_HTML_WITH_BIO)
    assert result["founder_bio"] == "Alice is a serial entrepreneur who previously founded DataCo."
    assert result["has_email"] is True


SAMPLE_HTML_NO_BIO = '''
<html><body>
<div>&quot;founders&quot;:[{&quot;user_id&quot;:456,&quot;is_active&quot;:true,&quot;full_name&quot;:&quot;Bob Jones&quot;,&quot;title&quot;:&quot;CTO&quot;,&quot;avatar_thumb_url&quot;:&quot;&quot;,&quot;linkedin_url&quot;:&quot;&quot;,&quot;twitter_url&quot;:&quot;&quot;,&quot;has_email&quot;:false}],&quot;editUrl&quot;:&quot;x&quot;</div>
</body></html>
'''


def test_parse_founders_handles_missing_bio():
    result = parse_founders_from_html(SAMPLE_HTML_NO_BIO)
    assert result["founder_bio"] is None
    assert result["has_email"] is False
