from setuptools import setup, find_packages


setup(
    name='scrapingknife',
    version='0.1dev0',
    description='scraping tools',
    author='TakesxiSximada',
    author_email='sximada+scrapingknife@gmail.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        ''
    ],
    entry_points="""\
    [console_scripts]
    scrapingknife = scrapingknife:main
    """,
)
