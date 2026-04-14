import sys

# Write zero-width test fixture with actual Unicode chars
with open('tests/fixtures/zero_width_test.txt', 'w', encoding='utf-8') as f:
    f.write('# Test fixture: zero-width characters\n')
    f.write('password\u200b = "secret123"\n')
    f.write('user\u200cname = "admin"\n')
    f.write('admin\u200drole = "superuser"\n')
    f.write('api_key\u2060 = "sk-1234567890"\n')
    f.write('token\ufeff = "bearer xyz"\n')
    f.write('access\u200e = True\n')
    f.write('deny\u200f = False\n')
    f.write('hidden = "vi\u200bsi\u200bble"\n')
    f.write('# Comment has \u200b zero-width space\n')
    f.write('calc\u2061 = 42\n')
    f.write('mul\u2062 = 3.14\n')
    f.write('sep\u2063 = ","\n')
print('zero_width_test.txt written')

# Write homoglyph test fixture
with open('tests/fixtures/homoglyph_test.txt', 'w', encoding='utf-8') as f:
    f.write('# Test fixture: homoglyph substitutions\n')
    f.write('p\u0430ssword = "hacked"\n')  # Cyrillic а
    f.write('us\u0435rname = "admin"\n')   # Cyrillic е
    f.write('auth\u043er = "evil"\n')      # Cyrillic о
    f.write('im\u0440ort os\n')            # Cyrillic р
    f.write('a\u0441cess = True\n')        # Cyrillic с
    f.write('l\u03bfgin = True\n')         # Greek ο
    f.write('\u0412ool = True\n')          # Cyrillic В
    f.write('\u041cAX = 100\n')            # Cyrillic М
    f.write('\u041dOST = "evil.com"\n')    # Cyrillic Н
    f.write('adm\u0456n = "root"\n')       # Cyrillic і mixed
print('homoglyph_test.txt written')

# Write RTL test fixture
with open('tests/fixtures/rtl_test.txt', 'w', encoding='utf-8') as f:
    f.write('# Test fixture: RTL override exploits\n')
    f.write('access_level = "user"\n')
    f.write('allow\u202d = True\n')
    f.write('role\u202b = "admin"\n')
    f.write('flag\u202a = True\n')
    f.write('auth\u00adorize = True\n')
    f.write('is\u00a0admin = True\n')
print('rtl_test.txt written')

# Write whitespace test fixture
with open('tests/fixtures/whitespace_test.txt', 'w', encoding='utf-8') as f:
    f.write('# Test fixture: whitespace steganography\n')
    f.write('x = 1        \n')  # 8 trailing spaces
    f.write('y = 2\t\t \t\n')  # mixed trailing tabs/spaces
    f.write('def foo():\n')
    f.write('\t    pass\n')     # mixed indent: tab then spaces
    f.write('    return 1\n')
    f.write('z = 3         \n') # long trailing whitespace
print('whitespace_test.txt written')

# Write comment steganography fixture
with open('tests/fixtures/comment_test.txt', 'w', encoding='utf-8') as f:
    f.write('# Test fixture: comment steganography\n')
    f.write('# Hello\ufe0f World\n')          # Variation selector
    f.write('hidden = "H\u0308\u0308ello"\n')  # Combining diaeresis
    f.write('x = 1  # \u02b0modifier\n')       # Modifier letter
    f.write('payload = "da\u0327ta"\n')        # Combining cedilla
    f.write('attack = "a\u0300\u0301\u0302\u0303\u0304"\n')  # 5 combining chars
print('comment_test.txt written')
