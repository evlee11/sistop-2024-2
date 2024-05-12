import os
import math
import struct

class File():

    def __init__(self, name:str, size:int, initial_cluster:int, creation_date:str, update_date:str) -> None:
        self.name = name
        self.size = size
        self.initial_cluster = initial_cluster
        self.creation_date = self._formatDate(creation_date)
        self.update_date = self._formatDate(update_date)
        self.cluster_size = 2048
    
    def __str__(self) -> str:
        return self.name


    '''Formatea la fecha a un formato AAAA-MM-DD HH:MM:SS 
       por ejemplo 20221108182600 para 2022-11-08 18:26:00 '''
    def _formatDate(self, date:str) -> str:
        # Obtener los componentes de la fecha
        year = date[:4]
        month = date[4:6]
        day = date[6:8]
        hour = date[8:10]
        minute = date[10:12]
        second = date[12:14]

        # Formatear la fecha en el nuevo formato
        new_date = f"{year}-{month}-{day} {hour}:{minute}:{second}"
        return new_date
    

    '''Obtiene el contenido del archivo en el directorio 'FiUnamFS' '''
    def _getFileContent(self):
        start = self.initial_cluster * self.cluster_size
        
        try:
            # Si la lectura es correcta se retorna el contenido leído 'content'
            # si presenta fallos en el proceso retorna 'None'
            with open('fiunamfs.img', 'rb') as FiUnamFS:
                FiUnamFS.seek(start)
                content = FiUnamFS.read(self.size + 1)
            
            return content
        except:
            return None
    

    '''Realiza una copia del archivo en 'FiUnamFS' hacia la computadora local.
       Retorna 'True' si la copia ha sido exitosa, 'False' si no ha sido así.'''
    def copyToSystem(self, path:str) -> bool:

        if not os.path.exists(path + f'/{self.name}'):
            content = self._getFileContent()

            try:
                with open(path + f'/{self.name}', 'wb') as new_file:
                    new_file.write(content)
                return True
            except:
                return False
    
    '''Retorna una tupla, en la primer pocisión existe el número de clusters que 
       ocupa el archivo, en la segunda pocisión existe una lista con los clusters usados. '''
    def getClustersTaken(self) -> tuple[int, list]:

        clusters_taken = []
        num_clusters_taken = math.ceil(self.size / self.cluster_size)

        for i in range(self.initial_cluster, self.initial_cluster + num_clusters_taken):
            clusters_taken.append(i)

        return (num_clusters_taken, clusters_taken)


class FiUnamFS():

    def __init__(self, path:str, directory_entry_size:int) -> None:
        self.path = path
        self.system_name = self._readDirectory(0, 8)
        self.version = self._readDirectory(10, 4)
        self.volumen_label = self._readDirectory(20, 15)
        self.cluster_size = self._readDirectory(40, 4)
        self.num_clusters = self._readDirectory(45, 4)
        self.num_total_clusters = self._readDirectory(50, 4)
        self.directory_entry_size = directory_entry_size
    
    def __str__(self) -> str:
        return self.system_name
    
    def showDetails(self) -> None:
        print(f'Nombre Directorio: {self.system_name}\n' +
              f'Version: {self.version}\n' +
              f'Etiqueta de Volumen: {self.volumen_label}\n' +
              f'Tamaño de Cluster: {self.cluster_size}\n' +
              f'Num de Clusters: {self.num_clusters}\n' +
              f'Num Total de Clusters: {self.num_total_clusters}'
            )
    

    ''' 'readDirectory' retorna un dato de tipo <str> o bien <int> decimal según 
        lo que encuentre en el directorio mediante una lectura en modo binario a 
        partir una posición y desplazamiento definidos. '''
    def _readDirectory(self, start:int, reading_size:int):

        with open(self.path, 'rb') as _FiUnamFS:
            _FiUnamFS.seek(start)
            content = _FiUnamFS.read(reading_size)

        try:
            c, = struct.unpack('<I', content)
            return c
        
        except:
            return content.decode('ascii')
    

    '''Retorna una lista de objetos 'File' equivalentes a los archivos (entradas)
       contenidos en el directorio.'''
    def getFiles(self) -> list:

        num_files = (self.cluster_size * self.num_clusters) // self.directory_entry_size
        start = self.cluster_size
        files = []

        for i in range(num_files):
            file_name = self._readDirectory(start + (i * 64), 15)
            
            if '-' in file_name:            
                files.append(
                    File(
                        name = file_name[1:].strip(),
                        size = self._readDirectory(start + (i * 64) + 16, 4),
                        initial_cluster = self._readDirectory(start + (i * 64) + 20, 4),
                        creation_date = self._readDirectory(start + (i * 64) + 24, 14),
                        update_date = self._readDirectory(start + (i * 64) + 38, 14)
                    )
                )
        
        return files
    
    '''Copia un archivo de fuera del directorio 'FiUnamFS' hacia dentro de
       este mismo, requiere la ubicación del archivo en la computadora
       incluyendo el nombre del archivo a copiar ej: '/d:archivos/archivo.jpg'''
    def copyFromSystem(self, path:str):

        # Tamaño del archivo a copiar
        new_file_size = os.path.getsize(path)

        # Obtenemos el cluster inicial de donde se comenzará a
        # alamacenar el contenido del archivo a copiar.
        start = self._searchSpace(new_file_size)
        print(f'se pego en cluster inicial = {start}')
        if start != None:
            # Movemos nuestro 'apuntador' a donde inicia el cluster obtenido
            # (cluster inicial * tamaño de cluster)
            start *= self.cluster_size
            content = self._getContentFile(path)

            try:
                with open(self.path, 'wb') as new_file:
                    new_file.seek(start)
                    new_file.write(content)
                
                # Si se copio con éxito
                return True
            except:
                print('Error al copiar contenido.')
                return False
            
        print('No existe espacio suficiente para copiar el archivo.')
        return False


    def _searchSpace(self, new_file_size:int):

       files_in_fiunamfs = self.getFiles()
       clusters_taken = []
       all_clusters = [i for i in range(self.num_total_clusters)]
       necessary_clusters = math.ceil(new_file_size / self.cluster_size)
       
       for file in files_in_fiunamfs:
           clusters_taken.extend(file.getClustersTaken()[1])
       
       # Elimina de 'all_clusters' todos aquellos clusters que esten ocupados. 
       for i in clusters_taken:
           if i in all_clusters:
               all_clusters.remove(i)

       # Buscamos una cantidad de clusters consecutivos del tamaño
       # necesario para almacenar el archivo nuevo (necessary_clusters).
       index = self._consecutiveSequence(all_clusters, necessary_clusters)
       if index != None:
           
           # Retorna el que deberá ser el cluster inicial
           return all_clusters[index]
       
       return None
           
        
    '''Busca una secuencia consecutiva de números en una lista, si la busqueda
       es exitosa retorna el índice de la lista donde inicia la secuencia.'''
    def _consecutiveSequence(self, lista, n):

        for i in range(len(lista) - n + 1):
            if all(lista[i + j] == lista[i] + j for j in range(n)):
                return i
              
        # Si no se encuentra ninguna secuencia consecutiva, devuelve None
        return None
    

    '''Obtiene el contenido de un archivo leído en modo binario. El archivo
       que se lee, es ajeno al directorio 'FiUnamFS', es decir, se encuentra
       fuera de este.'''
    def _getContentFile(self, path):
        
        try:
            with open(path, 'rb') as file:
                content = file.read()
            return content
        
        except:
            return None