name=		storpool-openstack-integration
version=	0.1.0_20150506

md=		README.md
html=		$(subst .md,.html,${md})

build=		$(CURDIR)/build
tools=		$(CURDIR)/tools

rel_cinder=	${build}/os-release-cinder
rel_nova=	${build}/os-release-nova

all:		driver

install:	cinder-install nova-install

clean:		driver-clean html-clean

cinder:		driver-detect-cinder driver-update-cinder

nova:		driver-detect-nova driver-update-nova

cinder-install:	driver-install-cinder

nova-install:	driver-install-nova

driver:		driver-detect driver-update

driver-detect:	driver-detect-cinder driver-detect-nova

driver-detect-cinder:	${rel_cinder}

driver-detect-nova:	${rel_nova}

${rel_cinder}:
		${tools}/detect-driver.pl -f cinder -d ${build} -o "$@"
		@echo "Detected OpenStack Cinder release: `cat $@`"
		@echo "Determined Python module directories:"
		@ls -l ${build}/
		${MAKE} driver-detect-consistent

${rel_nova}:
		${tools}/detect-driver.pl -f nova -d ${build} -o "$@"
		@echo "Detected OpenStack Nova release: `cat $@`"
		@echo "Determined Python module directories:"
		@ls -l ${build}/
		${MAKE} driver-detect-consistent

driver-detect-consistent:
		if [ -f "${rel_cinder}" ] && [ -f "${rel_nova}" ] && ! cmp -s -- "${rel_cinder}" "${rel_nova}"; then \
			echo "OpenStack release inconsistency: Cinder: `cat ${rel_cinder}`; Nova: `cat ${rel_nova}`"; \
			false; \
		fi

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

driver-install:	driver-install-cinder driver-install-nova

driver-install-cinder:
		set -e; \
		ref="${build}/install-ref"; \
		rm -f -- "$$ref"; \
		touch -- "$$ref"; \
		unset updated; \
		(cd ${build}/build-cinder && find ./ -type f) | while read f; do \
			src="${build}/build-cinder/$$f"; \
			dst="${build}/sys-cinder/$$f"; \
			if [ -e "$$dst" ]; then \
				${tools}/install-mimic.pl -v "$$src" "$$dst"; \
				if [ -z "$$updated" ]; then \
					${tools}/install-mimic.pl -v "$$src" "$$ref"; \
					updated=1; \
				fi; \
			fi; \
		done; \
		(cd ${build}/build-cinder && find ./ -type f) | while read f; do \
			src="${build}/build-cinder/$$f"; \
			dst="${build}/sys-cinder/$$f"; \
			if [ ! -e "$$dst" ]; then \
				${tools}/install-mimic.pl -v -r "$$ref" "$$src" "$$dst"; \
			fi; \
		done; \
		rm -f -- "$$ref"

driver-install-nova:
		set -e; \
		ref="${build}/install-ref"; \
		rm -f -- "$$ref"; \
		touch -- "$$ref"; \
		unset updated; \
		(cd ${build}/build-nova && find ./ -type f) | while read f; do \
			src="${build}/build-nova/$$f"; \
			dst="${build}/sys-nova/$$f"; \
			if [ -e "$$dst" ]; then \
				${tools}/install-mimic.pl -v "$$src" "$$dst"; \
				if [ -z "$$updated" ]; then \
					${tools}/install-mimic.pl -v "$$src" "$$ref"; \
					updated=1; \
				fi; \
			fi; \
		done; \
		(cd ${build}/build-nova && find ./ -type f) | while read f; do \
			src="${build}/build-nova/$$f"; \
			dst="${build}/sys-nova/$$f"; \
			if [ ! -e "$$dst" ]; then \
				${tools}/install-mimic.pl -v -r "$$ref" "$$src" "$$dst"; \
			fi; \
		done; \
		rm -f -- "$$ref"

driver-clean:
		rm -rf ${build}

.PHONY:		all clean driver-clean driver driver-install driver-detect
.PHONY:		driver-update driver-update-cinder driver-update-nova
.PHONY:		install driver-diff

html:		${html}

html-clean:
		rm -f ${html}

%.html:		%.md
		markdown "$<" > "$@" || (rm -f "$@"; false)

.PHONY:		html html-clean
