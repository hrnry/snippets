#!/usr/bin/env python3

# dev-python/lz4-0.8.2::gentoo

import lz4, os, sys

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('e.g.: ' + sys.argv[0] + ' search.json.mozlz4')
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = input_path

    if not os.path.isfile(input_path):
        print(input_path + ' is not file')
        sys.exit(2)

    print('input: ' + input_path)
    root, ext = os.path.splitext(input_path)
    with open(input_path, mode='rb') as f:
        if ext[-3:] == 'lz4':
            print('  lz4.decompress')
            if f.read(8) != b'mozLz40\0':
                f.seek(0)
            data = lz4.decompress(f.read())
            output_path = root
        else:
            print('  lz4.compress')
            data = b'mozLz40\0' + lz4.compress(f.read())
            output_path = root + ext + '.mozlz4'

    with open(output_path, mode='xb') as f:
        print('output: ' + output_path)
        f.write(data)
