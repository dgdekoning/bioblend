"""
A basic object-oriented interface for Galaxy entities.
"""

import json, hashlib


class Wrapper(object):

    def __init__(self, wrapped, parent=None):
        # http://stackoverflow.com/questions/2827623
        object.__setattr__(self, 'core', lambda: None)
        object.__setattr__(self, 'is_modified', False)
        object.__setattr__(self, 'parent', parent)
        setattr(self.core, 'wrapped', wrapped.copy())
        self.update_md5()

    def update_md5(self):
        md5 = hashlib.md5(json.dumps(self.core.wrapped)).hexdigest()
        object.__setattr__(self, 'md5', md5)

    def touch(self):
        object.__setattr__(self, 'is_modified', True)
        if self.parent:
            self.parent.touch()
        self.update_md5()

    def __getattr__(self, name):
        try:
            return self.core.wrapped[name]
        except KeyError:
            raise KeyError('no property with name "%s"' % name)

    def __setattr__(self, name, value):
        if name not in self.core.wrapped:
            raise KeyError('no property with name "%s"' % name)
        else:
            self.core.wrapped[name] = value
            self.touch()

    def __eq__(self, other):
        return  self.md5 == other.md5

    def __hash__(self):
        return self.md5

    def to_json(self):
        return json.dumps(self.core.wrapped)

    @classmethod
    def from_json(cls, jdef):
        return cls(json.loads(jdef))


class Tool(object):

    def __init__(self, step_dict, parent):
        self.step_dict = step_dict
        self.state = json.loads(step_dict['tool_state'])
        self.parent = parent

    @property
    def id(self):
        return self.step_dict['tool_id']

    @property
    def version(self):
        return self.step_dict['tool_version']

    @property
    def errors(self):
        return self.step_dict['tool_errors']

    @property
    def params(self):
        return self.state

    def __getitem__(self, key):
        return json.loads(self.state[key])

    def __setitem__(self, key, value):
        if key not in self.state:
            raise KeyError(key)
        self.state[key] = json.dumps(value)
        self.parent.touch()
        self.sync()

    def sync(self):
        self.step_dict['tool_state'] = json.dumps(self.state)


class Step(Wrapper):

    def __init__(self, step_dict, parent):
        super(Step, self).__init__(step_dict, parent)
        if step_dict['type'] == 'tool':
            setattr(self.core, 'tool', Tool(step_dict, self))

    @property
    def tool(self):
        return self.core.tool


class Workflow(Wrapper):

    KNOWN_FORMAT_VERSIONS = [u'0.1']

    def __init__(self, wf_dict, id=None, links=None):
        super(Workflow, self).__init__(wf_dict)
        steps = wf_dict['steps']
        setattr(self.core, 'steps',
                [Step(steps[str(i)], self) for i in xrange(len(steps))])
        if id is None:
            super(Workflow, self).touch()
        if links is not None:
            links = dict((d['label'], k) for k, d in links.iteritems())
        setattr(self.core, 'id', id)
        setattr(self.core, 'links', links)

    @property
    def steps(self):
        return self.core.steps

    @property
    def id(self):
        return self.core.id

    @property
    def links(self):
        return self.core.links

    def touch(self):
        super(Workflow, self).touch()
        # forget all Galaxy connections
        setattr(self.core, 'id', None)
        setattr(self.core, 'links', None)

    def clone(self):
        return self.__class__(self.core.wrapped.copy())

    def __eq__(self, other):
        return self.id == other.id and super(Workflow, self).__eq__(other)


class Library(Wrapper):

    def __init__(self, lib_dict, id=None):
        super(Library, self).__init__(lib_dict)
        setattr(self.core, 'id', id)

    @property
    def id(self):
        return self.core.id


class Folder(Wrapper):

    def __init__(self, f_dict, library):
        super(Folder, self).__init__(f_dict)
        setattr(self.core, 'library', library)

    @property
    def library(self):
        return self.core.library


class History(Wrapper):

    def __init__(self, hist_dict, datasets):
        super(History, self).__init__(hist_dict)
        setattr(self.core, 'datasets', datasets)

    @property
    def datasets(self):
        return self.core.datasets


class Dataset(Wrapper):

    def __init__(self, ds_dict, src):
        super(Dataset, self).__init__(ds_dict)
        setattr(self.core, 'src', src)

    @property
    def src(self):
        return self.core.src


class HistoryDatasetAssociation(Dataset):

    def __init__(self, ds_dict):
        super(HistoryDatasetAssociation, self).__init__(ds_dict, 'hda')


class LibraryDatasetDatasetAssociation(Dataset):

    def __init__(self, ds_dict):
        super(LibraryDatasetDatasetAssociation, self).__init__(ds_dict, 'ldda')


class LibraryDataset(Dataset):

    def __init__(self, ds_dict):
        super(LibraryDataset, self).__init__(ds_dict, 'ld')
