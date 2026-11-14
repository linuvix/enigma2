#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewindowstyle.h>
#include <lib/gui/ewindowstyleskinned.h>

DEFINE_REF(eWindowStyleSkinned);

eWindowStyleSkinned::eWindowStyleSkinned()
{
	// TODO: initialize colors!!
	m_listbox_border_set = 0;

	for (int i = 0; i < colMax; ++i)
	{
		m_gradient_set[i] = false;
		m_gradient_direction[i] = 0;
		m_gradient_alphablend[i] = false;
	}
}

void eWindowStyleSkinned::handleNewSize(eWindow *wnd, eSize &size, eSize &offset)
{
	size = eSize(
			size.width() + m_border[bsWindow].m_border_left + m_border[bsWindow].m_border_right,
			size.height() + m_border[bsWindow].m_border_top + m_border[bsWindow].m_border_bottom
		);

	offset = eSize(-m_border[bsWindow].m_border_left, -m_border[bsWindow].m_border_top);

	eWidget *child = wnd->child();

	wnd->m_clip_region = eRect(ePoint(0, 0), size);

	child->move(ePoint(m_border[bsWindow].m_border_left, m_border[bsWindow].m_border_top));
	child->resize(eSize(size.width() - m_border[bsWindow].m_border_left - m_border[bsWindow].m_border_right, size.height() - m_border[bsWindow].m_border_top - m_border[bsWindow].m_border_bottom));
}

void eWindowStyleSkinned::paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title)
{
	drawBorder(painter, eRect(ePoint(0, 0), wnd->size()), m_border[bsWindow], bpAll, 0);

	if (m_fnt)
	{
		painter.setBackgroundColor(m_color[colWindowTitleBackground]);
		painter.setForegroundColor(m_color[colWindowTitleForeground]);
		painter.setFont(m_fnt);
		painter.renderText(eRect(m_title_offset.width(), m_title_offset.height(), wnd->size().width() - m_title_offset.width(), m_border[bsWindow].m_border_top - m_title_offset.height()), title);
	}
}

void eWindowStyleSkinned::paintBackground(gPainter &painter, const ePoint &offset, const eSize &size)
{
	if (m_gradient_set[colBackground] && m_gradient_colors[colBackground].size() >= 2)
		painter.setGradient(m_gradient_colors[colBackground], m_gradient_direction[colBackground], m_gradient_alphablend[colBackground]);
	else
		painter.setBackgroundColor(m_color[colBackground]);
	painter.clear();
}

void eWindowStyleSkinned::setStyle(gPainter &painter, int what)
{
	int bgIndex = -1;
	int fgIndex = -1;

	switch (what)
	{
	case styleLabel:
		painter.setForegroundColor(m_color[colLabelForeground]);
		return;
	case styleListboxSelected:
		fgIndex = colListboxSelectedForeground;
		bgIndex = colListboxSelectedBackground;
		break;
	case styleListboxNormal:
		fgIndex = colListboxForeground;
		bgIndex = colListboxBackground;
		break;
	case styleListboxMarked:
		fgIndex = colListboxMarkedForeground;
		bgIndex = colListboxMarkedBackground;
		break;
	case styleListboxMarkedAndSelected:
		fgIndex = colListboxMarkedAndSelectedForeground;
		bgIndex = colListboxMarkedAndSelectedBackground;
		break;
	default:
		return;
	}

	if (fgIndex >= 0)
		painter.setForegroundColor(m_color[fgIndex]);

	if (bgIndex >= 0)
	{
		if (m_gradient_set[bgIndex] && m_gradient_colors[bgIndex].size() >= 2)
			painter.setGradient(m_gradient_colors[bgIndex], m_gradient_direction[bgIndex], m_gradient_alphablend[bgIndex]);
		else
			painter.setBackgroundColor(m_color[bgIndex]);
	}
}

void eWindowStyleSkinned::drawFrame(gPainter &painter, const eRect &frame, int what)
{
	int bs;
	switch (what)
	{
	case frameButton:
		bs = bsButton;
		break;
	case frameListboxEntry:
		bs = bsListboxEntry;
		break;
	default:
		eWarning("[eWindowStyleSkinned] invalid frame style %d", what);
		return;
	}
	drawBorder(painter, frame, m_border[bs], bpAll, gPainter::BT_ALPHABLEND);
}

int eWindowStyleSkinned::drawFrameRadius(gPainter &painter, const eRect &frame, int radius, uint8_t edges)
{
	if (m_listbox_border_set)
	{
		gRGB c = m_color[colListboxSelectedBorder];
		painter.setBackgroundColor(c);
		painter.setRadius(radius, edges);
		painter.drawRectangle(frame);
		return 1;
	}
	return 0;
}

void eWindowStyleSkinned::drawBorder(gPainter &painter, const eRect &pos, struct borderSet &border, int what, int flags)
{
	int x = pos.left(), xm = pos.right();

	ePtr<gPixmap>
		&tl = border.m_pixmap[bpiTopLeft],
		&t  = border.m_pixmap[bpiTop],
		&tr = border.m_pixmap[bpiTopRight],
		&l  = border.m_pixmap[bpiLeft],
		&r  = border.m_pixmap[bpiRight],
		&bl = border.m_pixmap[bpiBottomLeft],
		&b  = border.m_pixmap[bpiBottom],
		&br = border.m_pixmap[bpiBottomRight];

	if (tl)
	{
		painter.blit(tl, ePoint(x, pos.top()), eRect(), flags);
		x += tl->size().width();
	}

	if (tr)
	{
		xm -= tr->size().width();
		painter.blit(tr, ePoint(xm, pos.top()), pos, flags);
	}

	if (t)
	{
		while (x < xm)
		{
			painter.blit(t, ePoint(x, pos.top()), eRect(x, pos.top(), xm - x, pos.height()), flags);
			x += t->size().width();
		}
	}

	x = pos.left();
	xm = pos.right();

	if (bl)
	{
		painter.blit(bl, ePoint(pos.left(), pos.bottom()-bl->size().height()), eRect(), flags);
		x += bl->size().width();
	}

	if (br)
	{
		xm -= br->size().width();
		painter.blit(br, ePoint(xm, pos.bottom()-br->size().height()), eRect(x, pos.bottom()-br->size().height(), pos.width() - x, bl->size().height()), flags);
	}

	if (b)
	{
		while (x < xm)
		{
			painter.blit(b, ePoint(x, pos.bottom()-b->size().height()), eRect(x, pos.bottom()-b->size().height(), xm - x, pos.height()), flags);
			x += b->size().width();
		}
	}

	int y = 0;
	if (tl)
		y = tl->size().height();

	y += pos.top();

	int ym = pos.bottom();
	if (bl)
		ym -= bl->size().height();

	if (l)
	{
		while (y < ym)
		{
			painter.blit(l, ePoint(pos.left(), y), eRect(pos.left(), y, pos.width(), ym - y), flags);
			y += l->size().height();
		}
	}

	y = 0;

	if (tr)
		y = tr->size().height();

	y += pos.top();

	ym = pos.bottom();
	if (br)
		ym -= br->size().height();

	if (r)
	{
		while (y < ym)
		{
			painter.blit(r, ePoint(pos.right() - r->size().width(), y), eRect(pos.right()-r->size().width(), y, r->size().width(), ym - y), flags);
			y += r->size().height();
		}
	}
}

RESULT eWindowStyleSkinned::getFont(int what, ePtr<gFont> &fnt)
{
	fnt = 0;
	switch (what)
	{
	case fontStatic:
		fnt = new gFont("Regular", 12);
		break;
	case fontButton:
		fnt = new gFont("Regular", 20);
		break;
	case fontTitlebar:
		fnt = new gFont("Regular", 25);
		break;
	default:
		return -1;
	}
	return 0;
}

void eWindowStyleSkinned::setPixmap(int bs, int bp, ePtr<gPixmap> &ptr)
{
	setPixmap(bs, bp, *(ptr.operator->()));
}

void eWindowStyleSkinned::setPixmap(int bs, int bp, gPixmap &pixmap)
{
	if ((bs >= bsMax) || (bs < 0))
		return;

	int i = 0;
	for (int b = 1; b < bpMax; b <<= 1, ++i)
	{
		if (bp & b)
			m_border[bs].m_pixmap[i] = &pixmap;
	}

	m_border[bs].m_border_top = 0;
	m_border[bs].m_border_left = 0;
	m_border[bs].m_border_bottom = 0;
	m_border[bs].m_border_right = 0;

	for (int i = 0; i < 3; ++i)
		if (m_border[bs].m_pixmap[i])
			if (m_border[bs].m_border_top < m_border[bs].m_pixmap[i]->size().height())
				m_border[bs].m_border_top = m_border[bs].m_pixmap[i]->size().height();
	for (int i = 6; i < 9; ++i)
		if (m_border[bs].m_pixmap[i])
			if (m_border[bs].m_border_bottom < m_border[bs].m_pixmap[i]->size().height())
				m_border[bs].m_border_bottom = m_border[bs].m_pixmap[i]->size().height();

	if (m_border[bs].m_pixmap[3])
		m_border[bs].m_border_left = m_border[bs].m_pixmap[3]->size().width();
	else
		m_border[bs].m_border_left = 0;

	if (m_border[bs].m_pixmap[5])
		m_border[bs].m_border_right = m_border[bs].m_pixmap[5]->size().width();
	else
		m_border[bs].m_border_right = 0;
}

void eWindowStyleSkinned::setColor(int what, const gRGB &col)
{
	if ((what < colMax) && (what >= 0))
	{
		if (what == colListboxSelectedBorder)
			m_listbox_border_set = 1;
		m_color[what] = col;
	}
}

gRGB eWindowStyleSkinned::getColor(int what)
{
	if ((what < colMax) && (what >= 0))
		return m_color[what];
	return nullptr;
}

void eWindowStyleSkinned::setGradient(int what, const std::vector<gRGB> &colors, uint8_t direction, bool alphablend)
{
	if ((what < colMax) && (what >= 0) && colors.size() >= 2)
	{
		m_gradient_colors[what] = colors;
		m_gradient_direction[what] = direction;
		m_gradient_alphablend[what] = alphablend;
		m_gradient_set[what] = true;
	}
}

bool eWindowStyleSkinned::getGradient(int what, std::vector<gRGB> &colors, uint8_t &direction, bool &alphablend)
{
	if ((what < colMax) && (what >= 0) && m_gradient_set[what])
	{
		colors = m_gradient_colors[what];
		direction = m_gradient_direction[what];
		alphablend = m_gradient_alphablend[what];
		return true;
	}
	return false;
}

void eWindowStyleSkinned::clearGradient(int what)
{
	if ((what < colMax) && (what >= 0))
	{
		m_gradient_set[what] = false;
		m_gradient_colors[what].clear();
	}
}

void eWindowStyleSkinned::setTitleOffset(const eSize &offset)
{
	m_title_offset = offset;
}

void eWindowStyleSkinned::setTitleFont(gFont *fnt)
{
	m_fnt = fnt;
}
