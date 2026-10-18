# Bundled UI assets

The Courses UI uses native system fonts, with Georgia for the CourseLight
wordmark. No font files or runtime CDN requests are needed.

The original CourseLight bulb mark is a reusable SVG component in
`ui/shared/components/CourseLightMark.jsx`. Its gold globe, brown linework, and white
highlight complement the university logo; its base follows the header theme.

The header uses unmodified official Lehigh University PNG assets, bundled inline
so the component needs no external image requests. The brown version is shown
in light mode and the white version in dark mode. These university brand assets
remain Lehigh's trademarks; they are not part of the icon library's MIT license.

- [Brown logo](https://www2.lehigh.edu/themes/custom/lehigh/Lehigh-University-Logo_Brown.png)
  → `branding/lehigh-university-brown.png`
- [White logo](https://www2.lehigh.edu/sites/www2/files/Lehigh-University-Logo_White.png)
  → `branding/lehigh-university-white.png`
- Source: [Lehigh University assets and resources](https://www2.lehigh.edu/communications/assets-resources).

- File earmark arrow up, chevron down, and arrow up right from
  [Bootstrap Icons 1.13.1](https://icons.getbootstrap.com/), MIT license;
  see `icons/LICENSE.txt`. SVG files are unmodified upstream assets.
- The glass library license is in `licenses/liquid-glass.txt` and included in
  the generated bundle.
