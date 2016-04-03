# Pelican Imap Importer

Automatically copies content from text e-mails to your pelican content directory.

This allows you to send articles, pages, comments[^1], ... to a specific e-mail address and on the next site rebuild they will be automatically imported.

Author             | Website                       | Github
-------------------|-------------------------------|------------------------------
Bernhard Scheirle  | <http://bernhard.scheirle.de> | <https://github.com/Scheirle>

## Requirements (Python packages)
- keyring

## Setup
### Settings

Name          | Type     | Default    | Description
--------------|----------|------------|-------
`FOLDERS`     | `list`   | `[]`       | List containing all imap folders the plugin should watch
`HOST`        | `string` | `''`       | E-Mail provider
`USER`        | `string` | `''`       | login credentials
`TYPES`       | `dict`   | (see code) | Specifies where to copy the content
`FILE_FORMAT` | `string` | `md`       | File extension (currently only used by the `FILENAME` function)

#### The TYPES dict
The `TYPES`-`dict` contains different content types (articles, pages, comments, ...).
Each content type (is a `dict`) has a `PATH` and `FILENAME` member.

Name        | Type       | Description
------------|------------|---------|-------
`PATH`      | `string`   | Path to the folder in which the content should be copied. Relative to the Pelican `PATH` variable. Placeholders (`{my-metadata}`) will get replaced for each email.
`FILENAME`  | `function` | Optional. Function which returns the filename for the current email. The `number` function generates ongoing filenames.


### E-Mail
In order to detect the content correctly the e-mail has to be in a specific form:

	<Anything above this line will be ignored>
	-----BEGIN IMPORT BLOCK-----
	type: <the type of the content; as specified by TYPES >
	<arbitrary other metadata; will be used to replace placeholders in PATH>
	-----BEGIN CONTENT BLOCK-----
	<Content; Will not be validated; Simply copied into a file>
	-----END CONTENT/IMPORT BLOCK-----
	<Anything below this line will be ignored>

### Example
`pelicanconf.py`:

	def myFilenameFunc(path, metadata, content, settings):
		"""
		Returns the filename which should be used to store the content.

		path: absolute path to the parent folder
		metadata: email metadata 
		content: content of the file
		settings: pelican settings
		"""

	IMAP_IMPORTER = {
		'FOLDERS' : ['INBOX.PelicanImport', 'INBOX.Folder2']
		'HOST' : "example.org"
		'USER' : "me@example.org"
		'TYPES' : {
			'my-content-type' : {
				'PATH' : os.path.join('my-folder', '{my-metadata}'),
				'FILENAME' : myFilenameFunc,
			},
			'article' : {
				'PATH' : os.path.join('articles', '{category}'),
			},
			'comment' : {
				'PATH' : os.path.join('comments', '{slug}'),
				'FILENAME' : number,
			},
		}
	}

Let's say there is following e-mail in `INBOX.PelicanImport`:

	Hey Reader,
	below is my awesome article.
	-----BEGIN IMPORT BLOCK-----
	type: article
	category: demo
	filename: my-demo-article.md
	-----BEGIN CONTENT BLOCK-----
	title: My Demo Article

	[...]
	-----END CONTENT/IMPORT BLOCK-----
	
	Greetings Writer
	
Imap_importer will now copy the “My Demo Article” article (`CONTENT BLOCK`) to `articles/demo/my-demo-article.md`



## TODO
- Clean up 
- Optionally delete imported e-mails
- Setup helper (list imap folders)
- Fix some inconsistencies with `FILE_FORMAT`
- Improve Doc


[^1]: In conjunction with the [Pelican Comment System](https://github.com/getpelican/pelican-plugins/blob/master/pelican_comment_system/).