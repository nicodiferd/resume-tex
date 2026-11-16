# Local build. CI does the same with latexmk (see .github/workflows/build-resume.yml).
# Needs: python3 with requirements.txt installed, tectonic or latexmk, poppler.
PYTHON ?= python3
VARIANT ?= default

ifneq ($(shell command -v tectonic 2>/dev/null),)
TEX = tectonic --keep-logs
else
TEX = latexmk -pdf -interaction=nonstopmode -halt-on-error
endif

.PHONY: all render pdf check private clean

all: check

render:
	$(PYTHON) scripts/render.py --variant $(VARIANT)

pdf: render
	cd build && $(TEX) resume.tex

check: pdf
	$(PYTHON) scripts/check_pdf.py build/resume.pdf --tex build/resume.tex

# Private copy with a phone line. Reads RESUME_PHONE; writes build/private/.
private:
	@test -n "$$RESUME_PHONE" || { echo "set RESUME_PHONE first"; exit 1; }
	$(PYTHON) scripts/render.py --variant $(VARIANT) --out build/private
	cd build/private && $(TEX) resume.tex
	$(PYTHON) scripts/check_pdf.py build/private/resume.pdf --allow-phone

clean:
	rm -rf build
