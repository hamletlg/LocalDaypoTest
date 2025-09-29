import wx
import xml.etree.ElementTree as ET
import json
import os
import textwrap
import base64
import io

# --- 1. MODEL ---

class Question:
    """Represents a single question with its text, options, and answers."""
    def __init__(self, q_text, q_type, options, correct_indices, image_data=None):
        self.text = q_text
        self.type = q_type
        self.options = options
        self.correct_indices = correct_indices
        self.image_data = image_data
        self.user_answer_indices = []
        self.user_input = []
        self.is_answered = False
        self.is_correct = None

    def to_dict(self):
        return {
            'text': self.text,
            'user_answer_indices': self.user_answer_indices,
            'user_input': self.user_input,
            'is_answered': self.is_answered,
            'is_correct': self.is_correct
        }

    def from_dict(self, data):
        self.user_answer_indices = data.get('user_answer_indices', [])
        self.user_input = data.get('user_input', [])
        self.is_answered = data.get('is_answered', False)
        self.is_correct = data.get('is_correct', None)

class Test:
    """Manages the entire collection of questions and the test state."""
    def __init__(self):
        self.questions = []
        self.current_question_index = 0
        self.title = "Practice Test"

    @property
    def num_correct(self):
        return sum(1 for q in self.questions if q.is_correct is True)

    @property
    def num_incorrect(self):
        return sum(1 for q in self.questions if q.is_correct is False)
        
    @property
    def num_answered(self):
        return sum(1 for q in self.questions if q.is_answered)

# --- 2. CONTROLLER ---

class TestController:
    """Handles the application logic."""
    def __init__(self):
        self.test = Test()
        self.test_file = None
        self.progress_file = None

    def load_new_test_from_file(self, filepath):
        """Resets state and loads a new test from a specified XML file."""
        new_test = Test()
        
        try:
            xml_string = open(filepath, 'r', encoding='utf-8').read()
            it = ET.iterparse(io.StringIO(xml_string))
            for _, el in it:
                if '}' in el.tag:
                    el.tag = el.tag.split('}', 1)[1]
            root = ET.fromstring(xml_string)

            new_test.title = root.find('.//p/t').text or "Practice Test"

            images_data = {}
            image_container = root.find('i')
            if image_container is not None:
                for img_node in image_container.findall('i'):
                    img_key = img_node.get('p')
                    base64_full_string = img_node.text
                    if img_key and base64_full_string:
                        try:
                            _, base64_data = base64_full_string.split(',', 1)
                            image_bytes = base64.b64decode(base64_data)
                            images_data[img_key] = image_bytes
                        except (ValueError, base64.binascii.Error):
                            print(f"Warning: Could not decode image with key {img_key}")

            question_container = root.find('c')
            if question_container is None:
                wx.MessageBox("Invalid test format: No main question container (<c>) found.", "Load Error", wx.OK | wx.ICON_ERROR)
                return False

            for question_node in question_container.findall('c'):
                question_type_tag = question_node.find('t')
                if question_type_tag is None or question_type_tag.text is None:
                    continue
                
                q_type_code = question_type_tag.text
                
                p_tag = question_node.find('p')
                if p_tag is None:
                    continue
                q_text = "".join(p_tag.itertext()).strip()
                
                img_ref_node = question_node.find('b') 
                img_ref = img_ref_node.get('p') if img_ref_node is not None else None
                question_image_data = images_data.get(img_ref) if img_ref else None

                options = [opt.text.strip() if opt.text else "" for opt in question_node.findall('.//r/o')]
                answer_code = question_node.find('c').text

                q_type = None
                correct_indices = []

                if q_type_code == '1': # Single/Multiple Choice
                    correct_indices = [i for i, code in enumerate(answer_code) if code == '2']
                    q_type = 'single' if len(correct_indices) == 1 else 'multiple'
                
                elif q_type_code == '6': # Ordering Question
                    q_type = 'ordering'
                    if len(options) == 1 and ' ' in options[0]:
                        options = options[0].split()
                    
                    num_options = len(options)
                    answer_positions_str = textwrap.wrap(answer_code, 2)
                    answer_positions = [int(p) if p != '00' else num_options for p in answer_positions_str]
                    
                    sorted_options = []
                    for i, pos in enumerate(answer_positions):
                        if i < num_options:
                           sorted_options.append((pos, i))
                    
                    sorted_options.sort()
                    correct_indices = [original_index for pos, original_index in sorted_options]

                if q_type and options and correct_indices:
                    new_test.questions.append(Question(q_text, q_type, options, correct_indices, image_data=question_image_data))

            if not new_test.questions:
                wx.MessageBox("This XML file does not contain any valid questions.", "Load Error", wx.OK | wx.ICON_ERROR)
                return False

            self.test = new_test
            self.test_file = filepath
            
            basename = os.path.basename(filepath)
            self.progress_file = f"{os.path.splitext(basename)[0]}.progress.json"

            self.check_and_load_progress()
            
            return True

        except (FileNotFoundError, ET.ParseError) as e:
            wx.MessageBox(f"Error loading test file: {e}", "Load Error", wx.OK | wx.ICON_ERROR)
            return False
        
    def save_progress(self):
        if not self.progress_file: return
        progress_data = {
            'current_question_index': self.test.current_question_index,
            'questions': [q.to_dict() for q in self.test.questions]
        }
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=4)

    def check_and_load_progress(self):
        if not self.progress_file or not os.path.exists(self.progress_file): return
        dlg = wx.MessageDialog(None, "A previous session for this test was found. Do you want to continue?", "Resume Session?", wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() != wx.ID_YES:
            dlg.Destroy()
            return
        dlg.Destroy()
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            saved_questions_map = {q['text']: q for q in progress_data['questions']}
            for q_obj in self.test.questions:
                if q_obj.text in saved_questions_map:
                    q_obj.from_dict(saved_questions_map[q_obj.text])
            self.test.current_question_index = progress_data.get('current_question_index', 0)
        except (json.JSONDecodeError, KeyError) as e:
            wx.MessageBox(f"Could not load progress file: {e}", "Error", wx.OK | wx.ICON_ERROR)
            
    def get_current_question(self):
        if self.test and 0 <= self.test.current_question_index < len(self.test.questions):
            return self.test.questions[self.test.current_question_index]
        return None

    def evaluate_answer(self, user_answer, user_raw_input=None):
        question = self.get_current_question()
        if not question: return
        question.user_answer_indices = user_answer
        question.user_input = user_raw_input if user_raw_input is not None else user_answer
        question.is_answered = True
        
        if question.type == 'ordering':
            question.is_correct = (user_answer == question.correct_indices)
        else:
            question.is_correct = (sorted(user_answer) == sorted(question.correct_indices))
            
        return question.is_correct

    def next_question(self):
        if self.test and self.test.current_question_index < len(self.test.questions) - 1:
            self.test.current_question_index += 1
            return True
        return False

    def previous_question(self):
        if self.test and self.test.current_question_index > 0:
            self.test.current_question_index -= 1
            return True
        return False

# --- 3. VIEW ---

class TestFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(None, title="Practice Test", size=(1200, 800)) 
        self.controller = controller
        
        self.main_panel = wx.Panel(self)
        self.main_panel.SetBackgroundColour(wx.Colour(240, 240, 240))

        self.answer_controls = []
        # --- START OF CORRECTION: Sizer references for proper layout control ---
        self.content_sizer = None
        self.right_sizer = None
        # --- END OF CORRECTION ---

        self.make_menu_bar()
        self.create_widgets()
        self.update_view()
        self.Center()
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def make_menu_bar(self):
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN, "&Open Test...\tCtrl+O", "Open a new Daypo XML test file")
        file_menu.AppendSeparator()
        quit_item = file_menu.Append(wx.ID_EXIT)
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        self.SetMenuBar(menu_bar)
        self.Bind(wx.EVT_MENU, self.on_open_file, open_item)
        self.Bind(wx.EVT_MENU, self.on_quit, quit_item)

    def create_widgets(self):
        root_sizer = wx.BoxSizer(wx.VERTICAL)       
        self.content_sizer = wx.BoxSizer(wx.HORIZONTAL)       

        q_box = wx.StaticBox(self.main_panel, label="Question")
        left_sizer = wx.StaticBoxSizer(q_box, wx.VERTICAL)

        self.question_text = wx.StaticText(self.main_panel, style=wx.ALIGN_LEFT | wx.ST_NO_AUTORESIZE)
        font = self.question_text.GetFont()
        font.PointSize += 2
        self.question_text.SetFont(font)
        
        self.answer_sizer = wx.BoxSizer(wx.VERTICAL)

        left_sizer.Add(self.question_text, 0, wx.ALL | wx.EXPAND, 10)
        left_sizer.Add(wx.StaticLine(self.main_panel), 0, wx.EXPAND | wx.ALL, 10)
        left_sizer.Add(self.answer_sizer, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)

        exhibit_box = wx.StaticBox(self.main_panel, label="Exhibit")
        self.right_sizer = wx.StaticBoxSizer(exhibit_box, wx.VERTICAL)
        
        self.image_display = wx.StaticBitmap(self.main_panel)
        self.right_sizer.Add(self.image_display, 1, wx.ALL | wx.EXPAND, 10)

        self.content_sizer.Add(left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        self.content_sizer.Add(self.right_sizer, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 10)
        
        self.feedback_panel = wx.Panel(self.main_panel)
        self.feedback_text = wx.StaticText(self.feedback_panel, label="")
        font = self.feedback_text.GetFont()
        font.PointSize += 1
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.feedback_text.SetFont(font)

        feedback_sizer = wx.BoxSizer(wx.HORIZONTAL)
        feedback_sizer.Add(self.feedback_text, 1, wx.ALL | wx.EXPAND, 10)
        self.feedback_panel.SetSizer(feedback_sizer)
        self.feedback_panel.Hide()

        self.status_bar = self.CreateStatusBar(3)
        self.status_bar.SetStatusWidths([-3, -1, -1])

        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.prev_button = wx.Button(self.main_panel, label="< Previous")
        self.submit_button = wx.Button(self.main_panel, label="Submit Answer")
        self.next_button = wx.Button(self.main_panel, label="Next >")
        
        nav_sizer.Add(self.prev_button, 0, wx.ALL, 5)
        nav_sizer.AddStretchSpacer(1)
        nav_sizer.Add(self.submit_button, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        nav_sizer.AddStretchSpacer(1)
        nav_sizer.Add(self.next_button, 0, wx.ALL, 5)

        self.prev_button.Bind(wx.EVT_BUTTON, self.on_prev)
        self.submit_button.Bind(wx.EVT_BUTTON, self.on_submit)
        self.next_button.Bind(wx.EVT_BUTTON, self.on_next)

        root_sizer.Add(self.content_sizer, 1, wx.EXPAND)
        root_sizer.Add(self.feedback_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        root_sizer.Add(wx.StaticLine(self.main_panel), 0, wx.EXPAND | wx.ALL, 10)
        root_sizer.Add(nav_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.main_panel.SetSizer(root_sizer)

    def _bytes_to_bitmap(self, image_bytes, target_size):
        try:
            stream = io.BytesIO(image_bytes)
            image = wx.Image(stream)
            
            target_w, target_h = target_size
            
            if target_w > 0 and target_h > 0:
                img_w, img_h = image.GetSize()
                
                if img_w > target_w or img_h > target_h:
                    scale = min(target_w / img_w, target_h / img_h)
                    new_w, new_h = int(img_w * scale), int(img_h * scale)
                    
                    if new_w > 0 and new_h > 0:
                        image.Rescale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)

            return wx.Bitmap(image)
        except Exception as e:
            print(f"Error converting image bytes to bitmap: {e}")
            return wx.Bitmap()

    def update_view(self):
        # 1. PREPARACIÓN INICIAL: Limpiar el estado anterior
        self.answer_sizer.Clear(delete_windows=True)
        self.answer_controls.clear()
        self.feedback_panel.Hide()
        self.image_display.SetBitmap(wx.Bitmap())

        question = self.controller.get_current_question()
        if not question:
            self.content_sizer.Show(self.right_sizer, False)
            self.question_text.SetLabel("\n   Please open a test file to begin.\n\n   (File -> Open Test...)")
            self.submit_button.Disable()
            self.prev_button.Disable()
            self.next_button.Disable()
            self.SetTitle("Practice Test")
            self.status_bar.SetStatusText("No test loaded", 0)
            self.status_bar.SetStatusText("", 1)
            self.status_bar.SetStatusText("", 2)
            self.main_panel.Layout()
            return

        self.SetTitle(self.controller.test.title)
        self.question_text.SetLabel(question.text)
        
        # --- INICIO DE LA LÓGICA DE LAYOUT DEFINITIVA ---

        has_image = bool(question.image_data)
        
        # 2. CONFIGURAR VISIBILIDAD: Decidir si el panel de la imagen debe mostrarse.
        self.content_sizer.Show(self.right_sizer, has_image)

        # 3. TOMAR EL CONTROL DEL ANCHO DEL TEXTO (El paso clave)
        # Obtenemos el ancho total del área de cliente del panel principal.
        panel_width = self.main_panel.GetClientSize().width
        
        # Este será el ancho al que se debe ajustar el texto.
        wrap_width = 0
        
        if has_image:
            # LÓGICA 50/50: Si hay imagen, el texto DEBE ajustarse a la mitad del espacio.
            target_text_width = int(panel_width / 2)
            wrap_width = target_text_width - 25 # Restamos un poco de padding
        else:
            # Si no hay imagen, el texto puede usar casi todo el ancho disponible.
            wrap_width = panel_width - 25 # Restamos un poco de padding

        # Aplicamos el ajuste. Esto cambia el "tamaño mínimo requerido" del widget de texto,
        # obligándolo a ser más estrecho y alto. Solo lo hacemos si el ancho es válido.
        if wrap_width > 0:
            self.question_text.Wrap(wrap_width)
        
        # 4. EJECUTAR EL LAYOUT
        # Ahora que hemos reconfigurado el widget de texto, le pedimos al sizer que se recalcule.
        # El sizer verá que el panel de texto ya no necesita todo el ancho y distribuirá
        # el espacio sobrante al panel de la imagen, respetando la proporción 1:1.
        self.main_panel.Layout()

        # 5. DIBUJAR LA IMAGEN (SOLO DESPUÉS DE QUE EL LAYOUT SEA CORRECTO)
        # Ahora que el panel derecho tiene su tamaño final y correcto, creamos el bitmap.
        if has_image:
            container = self.right_sizer.GetStaticBox()
            available_size = container.GetClientSize()
            if available_size.width > 0 and available_size.height > 0:
                bitmap = self._bytes_to_bitmap(question.image_data, available_size)
                self.image_display.SetBitmap(bitmap)
        
        # --- FIN DE LA LÓGICA DE LAYOUT ---

        # 6. CREAR CONTROLES DE RESPUESTA (esto no cambia)
        if question.type == 'ordering':
            num_options = len(question.options)
            for i, option_text in enumerate(question.options):
                option_sizer = wx.BoxSizer(wx.HORIZONTAL)
                spin_ctrl = wx.SpinCtrl(self.main_panel, value='1', min=1, max=num_options, size=(130, -1))
                if question.is_answered and question.user_input:
                    spin_ctrl.SetValue(question.user_input[i])
                option_label = wx.StaticText(self.main_panel, label=option_text)
                option_sizer.Add(spin_ctrl, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
                option_sizer.Add(option_label, 1, wx.ALIGN_CENTER_VERTICAL)
                self.answer_sizer.Add(option_sizer, 0, wx.ALL, 5)
                self.answer_controls.append(spin_ctrl) 
        else:
            control_type = wx.CheckBox if question.type == 'multiple' else wx.RadioButton
            for i, option_text in enumerate(question.options):
                style = wx.RB_GROUP if (control_type == wx.RadioButton and i == 0) else 0
                control = control_type(self.main_panel, label=option_text, style=style)
                if i in question.user_answer_indices:
                    control.SetValue(True)
                self.answer_sizer.Add(control, 0, wx.ALL, 5)
                self.answer_controls.append(control)

        # 7. ACTUALIZAR UI FINAL
        self.update_feedback_and_nav(question)
        # Una última llamada a Layout para asegurar que los nuevos controles de respuesta se dibujen bien.
        self.main_panel.Layout()

    def update_feedback_and_nav(self, question):
        if question.is_answered:
            for control in self.answer_controls:
                control.Disable()

            if question.is_correct:
                self.feedback_text.SetLabel("Correct!")
                self.feedback_panel.SetBackgroundColour(wx.Colour(220, 255, 220))
            else:
                self.feedback_panel.SetBackgroundColour(wx.Colour(255, 220, 220))
                correct_options_text = ""
                if question.type == 'ordering':
                    ordered_options = [question.options[i] for i in question.correct_indices]
                    correct_options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(ordered_options)])
                    self.feedback_text.SetLabel(f"Incorrect. The correct order is:\n{correct_options_text}")
                else:
                    for i, control in enumerate(self.answer_controls):
                        is_correct = i in question.correct_indices
                        is_user_choice = i in question.user_answer_indices
                        if is_correct:
                            control.SetForegroundColour(wx.Colour(0, 150, 0))
                        elif is_user_choice and not is_correct:
                            control.SetForegroundColour(wx.Colour(200, 0, 0))
                    
                    correct_options_text = "\n".join([f"- {question.options[i]}" for i in question.correct_indices])
                    self.feedback_text.SetLabel(f"Incorrect. The correct answer(s) were:\n{correct_options_text}")
            
            self.feedback_panel.Show()
            self.feedback_panel.GetSizer().Layout()
        else:
            for control in self.answer_controls:
                control.Enable()
                control.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))

        self.submit_button.Enable(not question.is_answered)
        self.prev_button.Enable(self.controller.test.current_question_index > 0)
        self.next_button.Enable(self.controller.test.current_question_index < len(self.controller.test.questions) - 1)
        q_num = self.controller.test.current_question_index + 1
        total_q = len(self.controller.test.questions)
        self.status_bar.SetStatusText(f"Question: {q_num} of {total_q}", 0)
        self.status_bar.SetStatusText(f"Correct: {self.controller.test.num_correct}", 1)
        self.status_bar.SetStatusText(f"Incorrect: {self.controller.test.num_incorrect}", 2)
        self.main_panel.Layout()

    def on_submit(self, event):
        question = self.controller.get_current_question()
        if not question: return

        user_indices = []
        if question.type == 'ordering':
            user_input_values = [ctrl.GetValue() for ctrl in self.answer_controls]
            if len(set(user_input_values)) != len(question.options):
                wx.MessageBox("Each item must have a unique order number.", "Invalid Answer", wx.OK | wx.ICON_ERROR)
                return
            sorted_options = sorted(enumerate(user_input_values), key=lambda x: x[1])
            user_indices = [index for index, value in sorted_options]
            self.controller.evaluate_answer(user_indices, user_raw_input=user_input_values)
        else:
            user_indices = [i for i, control in enumerate(self.answer_controls) if control.GetValue()]
            self.controller.evaluate_answer(user_indices)

        self.update_feedback_and_nav(self.controller.get_current_question())

    def on_next(self, event):
        if self.controller.next_question():
            self.update_view()
        else:
            self.show_summary()

    def on_prev(self, event):
        if self.controller.previous_question():
            self.update_view()

    def on_open_file(self, event):
        with wx.FileDialog(self, "Open XML test file", wildcard="XML files (*.xml)|*.xml", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL: return
            pathname = fileDialog.GetPath()
            if self.controller.load_new_test_from_file(pathname):
                self.update_view()

    def show_summary(self):
        total, correct, incorrect = len(self.controller.test.questions), self.controller.test.num_correct, self.controller.test.num_incorrect
        summary_message = f"Test Finished!\n\nTotal Questions: {total}\nCorrect Answers: {correct}\nIncorrect Answers: {incorrect}"
        incorrect_questions = [q for q in self.controller.test.questions if not q.is_correct]
        if incorrect_questions:
            summary_message += "\n\nDo you want to retry the questions you got wrong?"
            dialog = wx.MessageDialog(self, summary_message, "Test Summary", wx.YES_NO | wx.ICON_INFORMATION)
            if dialog.ShowModal() == wx.ID_YES: self.retry_incorrect(incorrect_questions)
            dialog.Destroy()
        else:
            summary_message += "\n\nExcellent work! You answered all questions correctly."
            dialog = wx.MessageDialog(self, summary_message, "Test Summary", wx.OK | wx.ICON_INFORMATION)
            dialog.ShowModal()
            dialog.Destroy()

    def retry_incorrect(self, incorrect_questions):
        for q in incorrect_questions:
            q.user_answer_indices, q.user_input, q.is_answered, q.is_correct = [], [], False, None
        self.controller.test.questions = incorrect_questions
        self.controller.test.current_question_index = 0
        self.update_view()

    def on_quit(self, event):
        self.Close()
        
    def on_close(self, event):
        if self.controller.test_file:
            self.controller.save_progress()
        self.Destroy()

# --- 4. Main Application Entry Point ---
class App(wx.App):
    def OnInit(self):
        controller = TestController()
        frame = TestFrame(controller)
        frame.Show()
        return True

if __name__ == '__main__':
    app = App()
    app.MainLoop()
