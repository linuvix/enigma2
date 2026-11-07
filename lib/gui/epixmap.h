#ifndef __lib_gui_epixmap_h
#define __lib_gui_epixmap_h

#include <lib/gui/ewidget.h>
#include <vector>

class ePixmap : public eWidget {
	int m_alphatest;
	int m_scale;
public:
	ePixmap(eWidget* parent);
	~ePixmap();

	void setPixmap(gPixmap* pixmap);
	void setPixmap(ePtr<gPixmap>& pixmap);
	void setPixmapFromFile(const char* filename);
	void setPixmapFromFile(const char* filename, bool autoDetect); // OpenATV compat overload
	void setAlphatest(int alphatest); /* 1 for alphatest, 2 for alphablend */
	void setScale(int scale); // DEPRECATED
	void setPixmapScale(int flags);
	void setPixmapScaleFlags(int flags) { setPixmapScale(flags); } // DEPRECATED

	/* OpenPLi border API — kept unchanged */
	void setBorderWidth(int pixel);
	void setBorderColor(const gRGB& color);

	/* OpenATV animation API — present, non-functional in this build */
	void setAniPixmapFromFile(const char* filename, bool autostart = false);
	void startAnimation(bool once = false) { (void)once; }
	void stopAnimation() {}
	eSize getPixmapSize() const { return m_pixmap ? m_pixmap->size() : eSize(0, 0); }

protected:
	ePtr<gPixmap> m_pixmap;
	int event(int event, void* data = 0, void* data2 = 0);
	void checkSize();

private:
	enum eLabelEvent {
		evtChangedPixmap = evtUserWidget,
	};

	/* OpenPLi border state — kept unchanged */
	bool m_have_border_color;
	int m_border_width;
	gRGB m_border_color;
};

#endif
