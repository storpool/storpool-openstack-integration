name=		storpool-openstack-integration
version=	0.1.0_20150506

md=		README.md
html=		$(subst .md,.html,${md})

build=		$(CURDIR)/build
tools=		$(CURDIR)/tools

all:		${html}

driver:		driver-detect driver-update

driver-detect:	${build}/os-release

$(build)/os-release:
		${tools}/detect-driver.pl -d ${build}
		@echo "Detected OpenStack release: `cat $@`"
		@echo "Determined Python module directories:"
		@ls -l ${build}/

driver-update:	driver-update-cinder driver-update-nova

driver-update-cinder:
		${tools}/update-driver.pl -f cinder -t ${build}/tpl-cinder ${build}/sys-cinder ${build}/build-cinder

driver-update-nova:
		${tools}/update-driver.pl -f nova -t ${build}/tpl-nova ${build}/sys-nova ${build}/build-nova
		
driver-diff:
		set -e; for flavor in cinder nova; do \
			(cd ${build}/build-$$flavor && find ./ -type f) | while read f; do \
				diff -uN "${build}/sys-$$flavor/$$f" "${build}/build-$$flavor/$$f" || true; \
			done; \
		done

driver-install:
		set -e; \
		ref="${build}/install-ref"; \
		rm -f -- "$$ref"; \
		touch -- "$$ref"; \
		unset updated; \
		for flavor in cinder nova; do \
			(cd ${build}/build-$$flavor && find ./ -type f) | while read f; do \
				src="${build}/build-$$flavor/$$f"; \
				dst="${build}/sys-$$flavor/$$f"; \
				if [ -e "$$dst" ]; then \
					${tools}/install-mimic.pl -v "$$src" "$$dst"; \
					if [ -z "$$updated" ]; then \
						${tools}/install-mimic.pl -v "$$src" "$$ref"; \
						updated=1; \
					fi; \
				fi; \
			done; \
		done; \
		for flavor in cinder nova; do \
			(cd ${build}/build-$$flavor && find ./ -type f) | while read f; do \
				src="${build}/build-$$flavor/$$f"; \
				dst="${build}/sys-$$flavor/$$f"; \
				if [ ! -e "$$dst" ]; then \
					${tools}/install-mimic.pl -v -r "$$ref" "$$src" "$$dst"; \
				fi; \
			done; \
		done; \
		rm -f -- "$$ref"

clean:		driver-clean
		rm -f ${html}

driver-clean:
		rm -rf ${build}

.PHONY:		all clean driver-clean driver driver-install driver-detect
.PHONY:		driver-update driver-update-cinder driver-update-nova
.PHONY:		driver-diff driver-install

%.html:		%.md
		markdown "$<" > "$@" || (rm -f "$@"; false)
