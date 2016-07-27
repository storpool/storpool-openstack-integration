name=		storpool-openstack-integration
version=	0.2.1.dev20160727

md=		README.md
html=		$(subst .md,.html,${md})

all:		html

clean:		html-clean

html:		${html}

html-clean:
		rm -f ${html}

%.html:		%.md
		markdown "$<" > "$@" || (rm -f "$@"; false)

.PHONY:		all clean html html-clean
