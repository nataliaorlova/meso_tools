
#!/usr/bin/env python

from setuptools import setup
from setuptools.command.install import install as _install

class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()

if __name__ == '__main__':
    setup(
        name = 'tashtools',
        version = '0.1.1',
        description = 'tools to access and massage 2p meso data ',
        long_description = '',
        author = 'Natalia Orlova',
        author_email = 'nathali.orlova@gmail.com',
        license = '',
        url = 'https://github.com/nataliaorlova/tashtools',
        scripts = [],
        packages = [
            'tashtools',
        ],
        namespace_packages = [],
        py_modules = [
           # 'tashtools', <- these are single files

        ],
        classifiers = [
            'Development Status :: 3 - Alpha',
            'Programming Language :: Python'
        ],
        entry_points = {
           #'console_scripts': ['mouse_director=mousedirector:main'] <--- if you want to create exes
        },
        data_files = [],  # these are non-python files but you almost never want this
        package_data = {},
        install_requires = [  # your requirements
            'tifffile',
            'h5py',
            'numpy',
            'scipy',
            'matplotlib'

        ],
        dependency_links = [],
        zip_safe = True,
        cmdclass = {'install': install},
        keywords = '',
        python_requires = '',
        obsoletes = [],
    )

