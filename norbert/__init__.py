#!/usr/bin/env python
#
#   norbert.py - command line NBT editor
#
#   Copyright (C) 2012-2013 DMBuce <dmbuce@gmail.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

__all__ = [ "exceptions" ]
from . import *

import optparse
import sys
from nbt import nbt
import codecs

VERSION = "0.5"
DEFAULT_MAXDEPTH = 8
DEFAULT_PRINTFORMAT = "human"
DEFAULT_INPUTFORMAT = "nbt"
DEFAULT_SEP = "/#="

formatters = {}
readers = {}

tag_types = {
    nbt.TAG_END:        "TAG_End",
    nbt.TAG_BYTE:       "TAG_Byte",
    nbt.TAG_SHORT:      "TAG_Short",
    nbt.TAG_INT:        "TAG_Int",
    nbt.TAG_LONG:       "TAG_Long",
    nbt.TAG_FLOAT:      "TAG_Float",
    nbt.TAG_DOUBLE:     "TAG_Double",
    nbt.TAG_BYTE_ARRAY: "TAG_Byte_Array",
    nbt.TAG_STRING:     "TAG_String",
    nbt.TAG_LIST:       "TAG_List",
    nbt.TAG_COMPOUND:   "TAG_Compound",
    nbt.TAG_INT_ARRAY:  "TAG_Int_Array",

    "TAG_End":        nbt.TAG_END,
    "TAG_Byte":       nbt.TAG_BYTE,
    "TAG_Short":      nbt.TAG_SHORT,
    "TAG_Int":        nbt.TAG_INT,
    "TAG_Long":       nbt.TAG_LONG,
    "TAG_Float":      nbt.TAG_FLOAT,
    "TAG_Double":     nbt.TAG_DOUBLE,
    "TAG_Byte_Array": nbt.TAG_BYTE_ARRAY,
    "TAG_String":     nbt.TAG_STRING,
    "TAG_List":       nbt.TAG_LIST,
    "TAG_Compound":   nbt.TAG_COMPOUND,
    "TAG_Int_Array":  nbt.TAG_INT_ARRAY
}

complex_tag_types = [
    nbt.TAG_LIST,
    nbt.TAG_COMPOUND
]

def parse_args():
    usage = "%prog [options] [tag] [tag2] [tag3] ..." #TODO: man page
    desc  = "Edits or displays an NBT file. " \
            "<tag>s are given in norbert(5) format, with the tag type and value " \
            "optionally omitted. With the default arguments, it has the form <name> or " \
            "<name>=[[(type)]value]. In the first form, the tag corresponding to <name> is " \
            "printed. In the second form, <type> is ignored and the tag is set to the " \
            "given <value>. No changes are made on disk, however, unless '-o' is used. See " \
            "norbert(5), sections 'Names' and 'Values', for more detailed " \
            "descriptions of the format of <name> and <value>."
    parser = optparse.OptionParser(version=VERSION, usage=usage,
                                   description=desc)
    parser.add_option("-f", "--input-file",
                      dest="infile",
                      default="level.dat",
                      help="The file to read. Default is level.dat.") #TODO: support stdin
    parser.add_option("-o", "--output-file",
                      dest="outfile",
                      default=None,
                      help="The file to write to. If not provided, " \
                           "any changes made with <tag>=<value> arguments " \
                           "won't be written to disk.")
    parser.add_option("-p", "--print-format",
                      dest="format",
                      default=DEFAULT_PRINTFORMAT,
                      help="Format to print output in. " \
                           "Valid values are \"human\", \"nbt-txt\" " \
                           "and \"norbert\". " \
                           "Default is \"" + DEFAULT_PRINTFORMAT + "\".") #TODO: add "nbt", "json"
    parser.add_option("-i", "--input-format",
                      dest="inputformat",
                      default=DEFAULT_INPUTFORMAT,
                      help="Format of the input file. " \
                           "Valid values are \"nbt\" and \"norbert\". " \
                           "Default is \"" + DEFAULT_INPUTFORMAT + "\".") #TODO: add "json"
    parser.add_option("-d", "--depth",
                      dest="maxdepth",
                      type="int",
                      default=DEFAULT_MAXDEPTH,
                      help="Set the maximum recursion depth. Use 0 for no " \
                           "limit. Default is " + str(DEFAULT_MAXDEPTH) + ".")
    parser.add_option("-s", "--separator",
                      dest="sep",
                      default=DEFAULT_SEP,
                      help="Set the tag separator for norbert-formatted " \
                           "arguments, input, and output. " \
                           "The argument to this option must be " \
                           "a string between 1 and 3 characters long. " \
                           "The first character is used to delimit tag " \
                           "names, the second character is used to " \
                           "delimit list indices, and the third character is used to " \
                           "separate names and values. Default is '" + DEFAULT_SEP + \
                           "'")
    #parser.add_option("-c", "--create",

    (options, args) = parser.parse_args()

    # if no tags are given, print starting from the top-level tag
    if len(args) == 0:
        args.append("")

    if len(options.sep) == 0 or len(options.sep) > len(DEFAULT_SEP):
        raise exceptions.InvalidOptionError(
            "-s",
            "Must be between 1 and %s characters" % str(len(DEFAULT_SEP)),
            options.sep
        )
    else:
        options.sep += DEFAULT_SEP[ len(options.sep) : len(DEFAULT_SEP) ]
        norbert_print_pre.sep = options.sep

    # validate input format
    if options.format not in formatters:
        raise exceptions.InvalidOptionError(
            "-p",
            "Unknown format",
            options.format
        )

    return (options, args)

def main():
    try:
        # parse and validate arguments
        (options, args) = parse_args()
        # open file
        nbtfile = read_file(options, args)
    except exceptions.InvalidOptionError as e:
        err(e.strerror)
        return e.errno
    except IOError as e:
        err(e.strerror)
        return e.errno

    # read and/or set tags
    retval = 0
    for arg in args:
        r = norbert(nbtfile, options, arg)
        if r > retval:
            retval = r

    if retval != 0:
        return retval

    # write file if necessary
    if options.outfile is not None:
            nbtfile.write_file(options.outfile)

    return 0

def read_file(options, args):
    try:
        if options.inputformat in readers:
            reader = readers[options.inputformat]
            nbtfile = reader(options)
        else:
            err("Input format not recognized: " + options.inputformat)
            return None
    except IOError as e:
        # make sure error has strerror, errno
        if e.strerror is None:
            e.strerror = str(e)

        if options.infile not in e.strerror:
            e.strerror += ": '" + options.infile + "'"

        if e.errno is None or e.errno == 0:
            e.errno = exceptions.GENERAL_ERROR

        raise e

    return nbtfile

def nbt_read_file(options):
    return nbt.NBTFile(options.infile)
readers["nbt"] = nbt_read_file

def norbert_read_file(options):
    nbtfile = nbt.NBTFile()
    with open(options.infile) as f:
        try:
            for line in f:
                # parse names/indexes, type, value of tag
                names, tag = norbert_parse_line(line, options.sep)
                # add tag to nbtfile
                norbert_add_tag(nbtfile, names, tag)
        except UnicodeDecodeError as e:
            raise IOError("Not a norbert file")

    return nbtfile

readers["norbert"] = norbert_read_file

# parses a norbert-formatted line, e.g.
#
#     norbert_parse_line("asdf.jkl#1#2 = (TAG_Short) 237")
#
# would return a (list, tag) pair with values
#
#     (["asdf", "jkl", 1, 2], nbt.Tag_Short(237))
#
def norbert_parse_line(line, sep=DEFAULT_SEP):
    line = line.strip()
    name, tagtype, value = norbert_split_line(line, sep[2])

    # validate user input
    if tagtype is None:
        err("Invalid or missing tag type: " + line)
        raise IOError(exceptions.INVALID_TYPE, "Not a norbert file")
    elif tagtype != nbt.TAG_COMPOUND and value is None:
        err("Tag value not found: " + line)
        raise IOError(exceptions.INVALID_VALUE, "Not a norbert file")

    # get the list of names/indexes
    names = norbert_split_name(name, sep)

    # create the tag
    if tagtype == nbt.TAG_LIST:
        listtype = tag_types[value]
        tag = nbt.TAG_List(type=nbt.TAGLIST[listtype])
    elif tagtype == nbt.TAG_COMPOUND:
        tag = nbt.TAG_Compound()
    else:
        tag = nbt.TAGLIST[tagtype]()
        retval = set_tag(tag, value)
        if retval != 0:
            err("Invalid tag value: " + line)
            raise IOError(retval, "Not a norbert file")

    return names, tag

# splits a norbert line into its name, type, and value
#
# examples:
#     "asdf.jkl = (TAG_String) blah blah = whatever"
#         -> ("asdf.jkl", TAG_String, "blah blah = whatever")
#     "foo.bar = (TAG_Compound) {0 Entries}"
#         -> ("foo.bar", TAG_Compound, None)
#     "one#2.three = (TAG_List) [0 TAG_Byte(s)]
#         -> ("one#2.three", TAG_List, "TAG_Byte")
#
# if type or value can't be determined, they are returned as None
#
def norbert_split_line(nametypevaluetriplet, sep):
    # initialize return values
    tagtype = None
    value = None
    name = None

    # parse name
    nametypevalue = nametypevaluetriplet.split(sep)
    name = nametypevalue.pop(0)
    name = name.strip()
    nametypevalue = sep.join(nametypevalue)

    # check if tagtype is given
    if nametypevalue.lstrip().startswith('(TAG_'):
        # parse tagtype
        nametypevalue = nametypevalue.split(')')
        try:
            tagtype = nametypevalue.pop(0)
            tagtype = tagtype.lstrip()
            tagtype = tagtype.lstrip('(')
            tagtype = tag_types[tagtype] # KeyError
        except:
            tagtype = None

        nametypevalue = ')'.join(nametypevalue)
        

    # parse value
    nametypevalue = nametypevalue.lstrip()
    try:
        if tagtype == nbt.TAG_STRING \
          or ( tagtype != nbt.TAG_COMPOUND and nametypevalue != "" ):
            value = codecs.getdecoder("unicode_escape")(nametypevalue)[0]
        # else value is None
    except:
        value = None

    return (name, tagtype, value)

# splits a full norbert name into its component names and indexes
#
# example:
#     "asdf.jkl"    -> ["asdf", "jkl"]
#     "one#2.three" -> ["one", 2, "three"]
#
def norbert_split_name(name, sep=DEFAULT_SEP):
    names = []
    for n in name.split(sep[0]):
        n, indexes = split_name(n, sep[1])
        names.append(n)
        for i in indexes:
            names.append(int(i))

    return names

# inserts a tag into an nbtfile, creating new TAG_List's and TAG_Compound's as
# necessary
#
def norbert_add_tag(nbtfile, names, newtag):
    # give the root TAG_Compound the right name
    nbtfile.name = names[0]
    names.pop(0)

    tag = nbtfile
    for i, name in enumerate(names):
        testtag = get_tag(tag, str(name))
        # tag already exists
        if testtag is not None:
            tag = testtag

        # add leaf node
        elif i+1 == len(names):
            tag = norbert_add_child(tag, name, newtag)

        # add a list
        elif isinstance(names[i+1], int):
            # list of basic tags
            if i+2 == len(names):
                listtype = newtag.id
            # list of lists
            elif isinstance(names[i+2], int):
                listtype = nbt.TAG_LIST
            # list of compounds
            else:
                listtype = nbt.TAG_COMPOUND

            tag = norbert_add_child(tag, name, \
                                    nbt.TAG_List(type=nbt.TAGLIST[listtype])
            )

        # add a compound
        else:
            tag = norbert_add_child(tag, name, nbt.TAG_Compound())

def norbert_add_child(tag, i, child):
    # insert child into list
    if tag.id == nbt.TAG_LIST:
        tag.tags.insert(i, child)
    # insert into compound tag
    elif tag.id == nbt.TAG_COMPOUND:
        child.name = i
        tag.tags.append(child)

    return child

def norbert(nbtfile, options, arg):
    name, value = split_arg(arg, options.sep[2])

    tag = get_tag(nbtfile, name, sep=options.sep)
    if tag is None:
        err("Tag not found: " + name)
        return exceptions.TAG_NOT_FOUND

    if value == None:
        # print the tag and its subtags
        print_subtags(tag, maxdepth=options.maxdepth, format=options.format)
        return 0
    else:
        # set the tag
        return set_tag(tag, value)

def split_arg(namevaluepair, sep):
    name, type, value = norbert_split_line(namevaluepair, sep)
    return (name, value)

def get_tag(tag, fullname, sep=DEFAULT_SEP):
    if fullname == "":
        return tag

    try:
        for i in fullname.split(sep[0]):
            try:
                tag = tag[i]
            except TypeError as e:
                tag = tag[int(i)]
            except KeyError as e:
                (i, indexes) = split_name(i, sep[1])
                tag = tag[i]
                for j in indexes:
                    tag = tag[j]
    except (KeyError, ValueError, TypeError, IndexError) as e:
        return None

    return tag

def split_name(nameindexlist, sep):
    nameindex = nameindexlist.split(sep)
    name = nameindex.pop(0)
    indexes = [ int(i) for i in nameindex ]

    return (name, indexes)

# sets the value of a tag
#
# returns: 0 if the tag is successfully set,
#          TAG_NOT_IMPLEMENTED if tag type not implemented,
#          TAG_CONVERSION_ERROR if value couldn't be converted
def set_tag(tag, value):
    try:
        if tag.id == nbt.TAG_BYTE:
            # convert to integer
            tag.value = int(value)
        elif tag.id == nbt.TAG_SHORT:
            # convert to integer
            tag.value = int(value)
        elif tag.id == nbt.TAG_INT:
            # convert to integer
            tag.value = int(value)
        elif tag.id == nbt.TAG_LONG:
            # convert to integer
            tag.value = int(value)
        elif tag.id == nbt.TAG_FLOAT:
            # convert to float
            tag.value = float(value)
        elif tag.id == nbt.TAG_DOUBLE:
            # convert to float
            tag.value = float(value)
        elif tag.id == nbt.TAG_BYTE_ARRAY:
            # convert to list of int's
            tag.value = [ int(i) for i in value.split(',') ]
        elif tag.id == nbt.TAG_INT_ARRAY:
            # convert to list of int's
            tag.value = [ int(i) for i in value.split(',') ]
        elif tag.id == nbt.TAG_STRING:
            # no conversion needed
            tag.value = value
        else:
            err("Writing for " + tag_types[tag.id] + " not implemented.")
            return exceptions.TAG_NOT_IMPLEMENTED
    except ValueError as e:
        err("Couldn't convert " + value + " to " + tag_types[tag.id] + '.')
        return exceptions.TAG_CONVERSION_ERROR

    return 0

# print a message to stderr
def err(message):
    sys.stderr.write(message + '\n')

# do nothing with a tag
#
# parameters:
#   tag: the tag to do nothing with
#   depth: the depth from the root ancestor tag
def nothing(tag, depth=None):
    pass

def is_parent_of(parent, child):
    return parent.id in complex_tag_types and child in parent.tags

# does a traversal of a tag and its subtags
#
# parameters
# ----------
#   tag:           the root tag to start traversing from
#   pre_action:    preorder action
#   post_action:   postorder action
#   maxdepth:      maximum depth level
def traverse_subtags(tag, maxdepth=DEFAULT_MAXDEPTH,
                     pre_action=nothing, post_action=nothing):
    # stack: a list of (tag, int) pairs
    # cur:   the current tag
    # prev:  the previous tag
    # c:     the index to the sibling to cur's right
    # p:     the index to the sibling to prev's right
    #
    #
    #     parent
    #      / \
    #   cur   parent.tags[c]
    #

    if tag == None:
        return

    stack = [ (tag, None) ]
    pre_action(tag)
    (prev, p) = (None, None)

    while len(stack) != 0:
        # get cur from top of the stack
        (cur, c) = stack[-1]

        # if cur is the root or a child of prev
        if len(stack) != maxdepth and \
           ( prev == None or is_parent_of(prev, cur) ):
            if cur.id in complex_tag_types and len(cur.tags) != 0:
                # push cur's first child on stack
                push_child(stack, cur, 0)

                # perform preorder action on newly added item
                pre_action(stack[-1][0])

        # if prev is a child of cur
        elif len(stack) != maxdepth and is_parent_of(cur, prev):
            # push cur's next child (prev's sibling) on stack
            if p is not None:
                push_child(stack, cur, p)

                # perform preorder action on newly added item
                pre_action(stack[-1][0])

        # cur and prev are identical
        else:
            # perform postorder action on cur and pop it
            post_action(cur)
            stack.pop()

        (prev, p) = (cur, c)

# pushes a child and the index of the next child (if any) on the stack
def push_child(stack, parent, i):
    if len(parent.tags) > i + 1:
        stack.append( (parent.tags[i], i + 1) )
    else:
        stack.append( (parent.tags[i], None) )

def print_subtags(tag, maxdepth=DEFAULT_MAXDEPTH, format=DEFAULT_PRINTFORMAT):
    (print_tag_init, print_tag_pre, print_tag_post, print_tag_done) = \
        formatters[format]
    print_tag_init(tag)
    traverse_subtags(tag, maxdepth=maxdepth,
                     pre_action=print_tag_pre, post_action=print_tag_post)
    print_tag_done(tag)



def human_print_init(tag):
    tag.depth = 0

def human_print_pre(tag):
    if tag.id in complex_tag_types:
        for child in tag.tags:
            child.depth = tag.depth + 1

    if tag.name is None:
        print('    ' * tag.depth + ": " + tag.valuestr())
    else:
        print('    ' * tag.depth + tag.name + ": " + tag.valuestr())

formatters["human"] = (human_print_init, human_print_pre, nothing, nothing)



def nbt_txt_print_init(tag):
    tag.depth = 0

def nbt_txt_print_pre(tag):
    if tag.id in complex_tag_types:
        for child in tag.tags:
            child.depth = tag.depth + 1

    if tag.depth < 0:
        return

    if tag.id == nbt.TAG_COMPOUND:
        value = str(len(tag.tags)) + " entries"
    elif tag.id == nbt.TAG_LIST:
        value = str(len(tag.tags)) + " entries of type " + tag_types[tag.tagID]
        for child in tag.tags:
            child.name = None
    elif tag.id == nbt.TAG_BYTE_ARRAY:
        value = '[' + str(len(tag.value)) + " bytes]"
    elif tag.id == nbt.TAG_INT_ARRAY:
        value = '[' + str(len(tag.value)) + " ints]"
    else:
        value = tag.valuestr()

    if tag.name is None:
        print('   ' * tag.depth + tag_types[tag.id] + ": " + value)
    else:
        print('   ' * tag.depth + tag_types[tag.id] + "(\"" + tag.name + \
              "\"): " + value
        )

    if tag.id in complex_tag_types:
        print('   ' * tag.depth + '{')

def nbt_txt_print_post(tag):
    if tag.id in complex_tag_types:
        print('   ' * tag.depth + '}')

formatters["nbt-txt"] = \
    (nbt_txt_print_init, nbt_txt_print_pre, nbt_txt_print_post, nothing)



def norbert_print_init(tag):
    tag.fullname = tag.name

def norbert_print_pre(tag):
    sep = norbert_print_pre.sep
    if tag.id in complex_tag_types and len(tag.tags) != 0:
        for i, child in enumerate(tag.tags):
            if tag.id == nbt.TAG_COMPOUND:
                child.fullname = tag.fullname + sep[0] + child.name
            elif tag.id == nbt.TAG_LIST:
                child.fullname = tag.fullname + sep[1] + str(i)
    else:
        if tag.id in [nbt.TAG_BYTE_ARRAY, nbt.TAG_INT_ARRAY]:
            value = '(' + tag_types[tag.id] + ') ' + \
                    ','.join(map(str, tag.value))
        elif tag.id == nbt.TAG_LIST:
            value = '(' + tag_types[tag.id] + ') ' + tag_types[tag.tagID]
        else:
            value = '(' + tag_types[tag.id] + ') ' \
                    + codecs.getencoder("unicode_escape")(tag.valuestr())[0].decode("utf-8")

        print(tag.fullname + ' ' + sep[2] + ' ' + value)

norbert_print_pre.sep = DEFAULT_SEP

formatters["norbert"] = \
    (norbert_print_init, norbert_print_pre, nothing, nothing)



if __name__ == "__main__":
    sys.exit(main())

