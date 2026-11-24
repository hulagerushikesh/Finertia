"""Share pages and cards for a set-up."""

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError

import share
from api.core import (
    ALLOWED_ORIGINS,
    client_ip,
    share_limiter,
)
from api.simulation import simulate
from schemas import BacktestRequest

router = APIRouter()

# Previews are rate limited by share_limiter (api/core.py): per address, and
# only on a cache miss.
_SHARE_CACHE = {"Cache-Control": "public, max-age=3600, s-maxage=86400"}


def _share_figures(request: Request):
    """(canonical query, figures) for a single-stock link, or None if it is not one."""
    params = request.query_params
    if params.get("mode", "single") != "single":
        return None
    try:
        req = BacktestRequest(**{k: v for k, v in params.items() if k in BacktestRequest.model_fields})
    except ValidationError:
        return None
    query = share.canonical_query(req)
    fig = share.cache.get(query)
    if fig is None:
        if not share_limiter.check(client_ip(request))["allowed"]:
            raise HTTPException(status_code=429, detail="Too many previews from this address. Try again in a minute.")
        close, _, engine_out, benchmark, _ = simulate(req)
        fig = share.figures(req, close, engine_out, benchmark)
        share.cache.put(query, fig)
    return query, fig


@router.get("/share")
def share_page(request: Request):
    """The preview page for a shared set-up; people are sent on to the workspace."""
    if not share.enabled():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        found = _share_figures(request)
    except HTTPException as exc:
        if exc.status_code == 429:
            raise
        found = None  # a bad ticker or Yahoo down: the workspace explains it better
    if found is None:
        # Relative, so it stays on the site the link was opened on.
        return RedirectResponse(f"/dashboard?{urlencode(list(request.query_params.multi_items()))}", status_code=302)
    query, fig = found
    site = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://localhost:5174"
    return HTMLResponse(share.page(fig, query, site), headers=_SHARE_CACHE)


@router.get("/share/card.png")
def share_card(request: Request):
    """The 1200x630 card the preview page names as its og:image."""
    if not share.enabled():
        raise HTTPException(status_code=404, detail="Not found")
    found = _share_figures(request)
    if found is None:
        raise HTTPException(status_code=404, detail="No card for this link")
    return Response(share.card(found[1]), media_type="image/png", headers=_SHARE_CACHE)

