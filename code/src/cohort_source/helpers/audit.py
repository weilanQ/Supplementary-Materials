

def fetch(path,obj):
 for p in path.split('/')[1:]:obj=obj[int(p)] if isinstance(obj,list) else obj[p]
 return obj
