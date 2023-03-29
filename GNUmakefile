# SPDX-FileCopyrightText: 2015 - 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0

name=		storpool-openstack-integration
version=	1.0.0

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
