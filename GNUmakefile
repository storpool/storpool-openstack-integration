name=		storpool-openstack-integration
version=	0.1.0_20150506

md=		README.md
html=		$(subst .md,.html,${md})

all:		${html}

clean:
		rm -f ${html}

%.html:		%.md
		markdown "$<" > "$@" || (rm -f "$@"; false)
