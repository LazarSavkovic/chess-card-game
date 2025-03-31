let userId = null;
const userH2 = document.getElementById('userH2')
const turnH5 = document.getElementById('turnH5')
const endTurnBtn = document.getElementById("endTurnBtn")
userH2.innerText = `User: ${userId}`
const cellSize = 10;
const pathParts = window.location.pathname.split('/'); 
const roomId = pathParts[pathParts.length - 1]; // Get the last part of the path
console.log('room id', roomId)
const gameId = "demo"; // static for now
const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${protocol}://${location.host}/game/${roomId}`);

const boardEl = document.getElementById('board');
let selected = null;
let board = [];
let hand1 = [];
let hand2 = [];
let graveyard1 = [];
let graveyard2 = [];
let mana = { '1': 50, '2': 50 };

let turn = '1';
let selectedHandIndex = null;
let lastSummonedPos = null;

function flipDirection(dir) {
  const flipMap = {
    "forward": "back",
    "back": "forward",
    "left": "right",
    "right": "left",
    "forward-left": "back-right",
    "forward-right": "back-left",
    "back-left": "forward-right",
    "back-right": "forward-left"
  };
  return flipMap[dir] || dir;
}




endTurnBtn.onclick = () => {
  ws.send(JSON.stringify({ type: 'end-turn', user_id: userId }));
};

ws.onopen = () => {
  ws.send(JSON.stringify({ user_id: userId }));
};
function playSound(id) {
  const audio = document.getElementById(id);
  if (audio) audio.play();
}
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.hand1, data.hand2);

  if (data.user_id && !userId) {
    userId = data.user_id;
    document.getElementById('userH2').innerText = `User: ${userId}`;
  }

  const myGrave = document.getElementById('graveyard');
  const oppGrave = document.getElementById('opponent-graveyard');
  if (userId === '1') {
    myGrave.style.borderColor = '#3399ff';
    oppGrave.style.borderColor = 'orange';
  } else {
    myGrave.style.borderColor = 'orange';
    oppGrave.style.borderColor = '#3399ff';
  }

  if (!data.board) return;

  board = data.board;
  if (turn != data.turn)
    notify('green', data.turn == userId ? 'Your turn' : "Opponent's turn");
  turn = data.turn;

  if (data.hand1) hand1 = data.hand1;
  if (data.hand2) hand2 = data.hand2;

  if (data.deck_sizes) {
    const myCount = data.deck_sizes[userId];
    const opponentId = userId === '1' ? '2' : '1';
    const opponentCount = data.deck_sizes[opponentId];
    document.getElementById('deckCount').innerText = `${myCount} card${myCount === 1 ? '' : 's'}`;
    document.getElementById('opponentDeckCount').innerText = `${opponentCount} card${opponentCount === 1 ? '' : 's'}`;
  }

  if (data.mana) {
    mana = data.mana;
    document.getElementById('manaH6').innerText = `Mana: ${mana[userId]}`;
    const opponentId = userId === '1' ? '2' : '1';
    document.getElementById('opponentManaH6').innerText = `Opponent Mana: ${mana[opponentId]}`;
  }

  if (data.graveyard) {
    if (data.graveyard['1']) graveyard1 = data.graveyard['1'];
    if (data.graveyard['2']) graveyard2 = data.graveyard['2'];
  }

  // 🔊 Play sounds
  if (data.success) {
    if (data.info?.includes("summoned")) {
      playSound("spawnSound");
      if (data.to) {
        lastSummonedPos = data.to.join("-");
      } else {
        lastSummonedPos = null;
      }
    } else {
      lastSummonedPos = null;
    }

    if (data.type === 'game-over') {
      if (data.game_over.result === 'victory') {
        notify("green", "🏆 Victory! You win!");
      } else if (data.game_over.result === 'defeat') {
        notify("red", "💀 You lose!");
      }
    
      // Optional: disable interactions
      document.getElementById("endTurnBtn").disabled = true;
      boardEl.style.pointerEvents = 'none';
    }
    

    if (data.info?.includes("Move successful")) {
      playSound("moveSound");
    }

    if (data.info?.includes("defeated") || data.info?.includes("killed")) {
      playSound("deathSound");
    }

    if (data.info?.includes("attacked directly")) {
      playSound("deathSound");
    }

    // 🪄 Optional: sound for sorcery (if using a "magicSound")
    if (data.info?.includes("activated") || data.info?.includes("cast")) {
      playSound("spawnSound"); // or use "magicSound" if you have one
    }
  }

  // 🖼️ Update visuals
  renderHand();
  renderOpponentHand();
  renderBoard();
  renderGraveyards();

  // 🔁 Moves left
  if (data.moves_left !== undefined) {
    document.getElementById('movesLeft').innerText = `Moves left: ${data.moves_left}`;
  }

  // ⚠️ Error handling
  if (data.info && !data.success) {
    notify('red', data.info);
  }
};

function renderHand() {
  const handDiv = document.getElementById('hand');
  handDiv.innerHTML = '';

  const playerHand = userId === '1' ? hand1 : hand2;

  playerHand.forEach((card, i) => {
    const cardEl = document.createElement('div');
    cardEl.className = `hand-card user-${card.owner}`;
    cardEl.style.backgroundImage = `url(${card.image})`;
    cardEl.style.backgroundSize = 'cover';
    cardEl.style.backgroundPosition = 'center';
    cardEl.style.position = 'relative';
    cardEl.style.color = 'white';
    cardEl.style.textShadow = '0 0 4px black';

    if (card.owner === userId) {
      // Add shared preview on hover
      cardEl.onmouseenter = () => {
        showCardPreview(card);
      };

      // 👾 Monster Card
      if (card.type === 'monster') {
        const info = document.createElement('div');
        info.className = 'card-info';
        info.innerText = `${card.name}\n${card.attack} / ${card.defense}`;
        styleCardInfo(info);
        cardEl.appendChild(info);

        cardEl.onclick = () => {
          selectedHandIndex = i;
          highlightSummonZones();
        };
      }

      // 🔥 Sorcery Card
      else if (card.type === 'sorcery') {
        const info = document.createElement('div');
        info.className = 'card-info';
        info.innerText = `${card.name}\n(Sorcery)`;
        styleCardInfo(info);
        cardEl.appendChild(info);

        const label = document.createElement('div');
        label.innerText = 'SORCERY';
        label.style.position = 'absolute';
        label.style.bottom = '4px';
        label.style.left = '4px';
        label.style.padding = '2px 4px';
        label.style.background = 'rgba(255, 255, 255, 0.2)';
        label.style.fontSize = '10px';
        label.style.color = 'white';
        label.style.borderRadius = '3px';
        cardEl.appendChild(label);

        cardEl.onclick = () => {
          selectedHandIndex = i;
          // For now, no special highlight
          highlightSorceryZones();  // 👈 new behavior
        };
      }

      // 🪨 Unknown type fallback
      else {
        const info = document.createElement('div');
        info.className = 'card-info';
        info.innerText = card.name;
        styleCardInfo(info);
        cardEl.appendChild(info);
      }

    } else {
      cardEl.innerText = '🂠'; // Back of opponent card
    }

    handDiv.appendChild(cardEl);
  });
}

function styleCardInfo(info) {
  info.style.position = 'absolute';
  info.style.top = '8px';
  info.style.left = '4px';
  info.style.right = '4px';
  info.style.fontSize = '11px';
  info.style.background = 'rgba(0, 0, 0, 0.5)';
  info.style.borderRadius = '4px';
}


function renderOpponentHand() {
  const opponentHandDiv = document.getElementById('opponent-hand');
  opponentHandDiv.innerHTML = '';

  const opponentHand = userId === '1' ? hand2 : hand1;

  opponentHand.forEach((card, i) => {
    const cardEl = document.createElement('div');
    cardEl.className = `hand-card opponent-card user-${card.owner}`;
    cardEl.innerText = '🂠'; // optional or just leave blank
    opponentHandDiv.appendChild(cardEl);
  });
}

function renderGraveyards() {
  const myGraveyard = document.getElementById('graveyard');
  const oppGraveyard = document.getElementById('opponent-graveyard');

  myGraveyard.innerHTML = '';
  oppGraveyard.innerHTML = '';

  const myGrave = userId === '1' ? graveyard1 : graveyard2;
  const oppGrave = userId === '1' ? graveyard2 : graveyard1;

  myGrave.forEach(card => {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'grave-card';
    cardDiv.style.backgroundImage = `url(${card.image})`;
    cardDiv.title = card.name;
    myGraveyard.appendChild(cardDiv);
  });

  oppGrave.forEach(card => {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'grave-card';
    cardDiv.style.backgroundImage = `url(${card.image})`;
    cardDiv.title = card.name;
    oppGraveyard.appendChild(cardDiv);
  });
}



function renderBoard() {
  document.querySelectorAll('.summon-zone').forEach(cell => {
    cell.classList.remove('summon-zone');
  });
  if (turn === userId){
    turnH5.innerText = "Your turn";
 

  } else {  
    turnH5.innerText = (turn === userId) ? "Your turn" : "Opponent's turn";
 
  }
 boardEl.innerHTML = '';

  const numRows = board.length;
  const numCols = board[0]?.length || 0;

  boardEl.style.gridTemplateColumns = `repeat(${numCols}, ${cellSize}vh)`;
  boardEl.style.gridTemplateRows = `repeat(${numRows}, ${cellSize}vh)`;

  const flipped = userId === '2';
  const rowRange = flipped ? [...Array(numRows).keys()].reverse() : [...Array(numRows).keys()];
  const colRange = flipped ? [...Array(numCols).keys()].reverse() : [...Array(numCols).keys()];



  for (let x of rowRange) {
    for (let y of colRange) {
      const cell = document.createElement('div');



      cell.className = 'cell ' + ((x + y) % 2 === 0 ? 'white' : 'black');
      cell.dataset.x = x;
      cell.dataset.y = y;


      const overlay = document.createElement('div');
      overlay.className = 'cell-overlay';
      cell.appendChild(overlay);

      const card = board[x][y];
      if (card) {
        const cardFrame = document.createElement('div');
        cardFrame.className = `card-frame ${card.owner === '1' ? 'user-1' : 'user-2'}`;

        if (`${x}-${y}` === lastSummonedPos) {
          cardFrame.classList.add("just-summoned");
          // Remove the class after animation ends
          cardFrame.addEventListener("animationend", () => {
            cardFrame.classList.remove("just-summoned");
          });
        }
        const imageDiv = document.createElement('div');
        imageDiv.className = 'card-image';
        imageDiv.style.backgroundImage = `url(${card.image})`;

        if (card.owner !== userId) {
          imageDiv.classList.add('flipped-image');
        }

        cardFrame.appendChild(imageDiv);


        cardFrame.style.position = 'relative';
        cardFrame.style.color = 'white';
        cardFrame.style.textShadow = '0 0 3px black';
        cardFrame.style.backdropFilter = 'brightness(0.8)';
        const overlay = document.createElement('div');
        overlay.className = 'overlay';
        cardFrame.appendChild(overlay);

        const nameDiv = document.createElement('div');
        nameDiv.className = 'card-name';
        nameDiv.textContent = card.name;
        cardFrame.appendChild(nameDiv);

        // 👉 Add the name as a tooltip
        cardFrame.title = card.name;

        cardFrame.onmouseenter = () => {
          showCardPreview(card);
        };

        
        const statsDiv = document.createElement('div');
        statsDiv.className = 'stats';
        cardFrame.appendChild(statsDiv);


        if (card.attack !== undefined && card.defense !== undefined) {
          const attackSpan = document.createElement('span');
          const defenseSpan = document.createElement('span');
        
          // Check for attack change
          if (card.attack > card.original_attack) {
            attackSpan.style.color = 'lime';
          } else if (card.attack < card.original_attack) {
            attackSpan.style.color = 'red';
          }
        
          // Check for defense change
          if (card.defense > card.original_defense) {
            defenseSpan.style.color = 'lime';
          } else if (card.defense < card.original_defense) {
            defenseSpan.style.color = 'red';
          }
        
          attackSpan.textContent = card.attack;
          defenseSpan.textContent = card.defense;
        
          statsDiv.appendChild(attackSpan);
          statsDiv.appendChild(document.createTextNode(' / '));
          statsDiv.appendChild(defenseSpan);
        }
        

        cell.appendChild(cardFrame);

        if (card.movement) {
          for (const dir in card.movement) {
            if (card.movement[dir]) {
              const finalDir = card.owner === userId ? dir : flipDirection(dir);
              const arrow = document.createElement('div');
              arrow.className = `movement movement-${finalDir}`;
              arrow.style.borderColor = (card.movement[dir] === 'any') ? 'red' : 'lime';
              cardFrame.appendChild(arrow);
            }
          }
        }

      }

      cell.onclick = () => handleClick(x, y, cell);
      boardEl.appendChild(cell);
    }
  }

  if (selectedHandIndex !== null) {
    highlightSummonZones();
  }

}

function showCardPreview(card) {
  const preview = document.getElementById('cardPreview');
  preview.innerHTML = '';

  const wrapper = document.createElement('div');
  wrapper.className = 'card-preview-frame';

  const name = document.createElement('div');
  name.className = 'card-preview-name';
  name.innerText = card.name;

  const image = document.createElement('div');
  image.className = 'card-preview-image';
  image.style.backgroundImage = `url(${card.image})`;

  const bottom = document.createElement('div');
  bottom.className = 'card-preview-bottom';

  if (card.attack && card.defense) {

    const stats = document.createElement('div');
    stats.className = 'card-preview-stats';
    stats.innerText = `ATK: ${card.attack} / DEF: ${card.defense}`;
    bottom.appendChild(stats);
  }
  console.log(card)

  if (card.text) {

    const text = document.createElement('div');
    text.className = 'card-preview-text';
    text.innerText = card.text;
    bottom.appendChild(text);
  }

  const mana = document.createElement('div');
  mana.className = 'card-preview-mana';
  mana.innerText = `Mana: ${card.mana || 0}`;

  const arrows = document.createElement('div');
  arrows.className = 'card-preview-arrows';

  if (card.movement) {
    for (const dir in card.movement) {
      if (card.movement[dir]) {
        const arrow = document.createElement('div');
        arrow.className = `movement movement-${dir}`;
        arrow.style.borderColor = card.movement[dir] === 'any' ? 'red' : 'lime';
        arrows.appendChild(arrow);
      }
    }
  }
  else if (card.type === 'sorcery' && Array.isArray(card.activation_needs)) {
    for (const dir of card.activation_needs) {
      const arrow = document.createElement('div');
      arrow.className = `movement movement-${dir}`;
      arrow.style.borderColor = 'white';
      arrows.appendChild(arrow);
    }
  }
  

  
  bottom.appendChild(mana);
  bottom.appendChild(arrows);

  wrapper.appendChild(name);
  wrapper.appendChild(image);
  wrapper.appendChild(bottom);

  preview.appendChild(wrapper);
}




function highlightSummonZones() {
  const validCols = [0, 3, 6];
  const summonRow = userId === '1' ? 6 : 0;

  validCols.forEach(col => {
    const selector = `.cell[data-x="${summonRow}"][data-y="${col}"]`;
    const cell = document.querySelector(selector);
    if (cell) {
      cell.classList.add('summon-zone');
    }
  });
}

function highlightMoves(x, y, card) {
  clearMoveHighlights();

  const movement = card.movement;
  const directions = {
    "forward": userId == 1 ? [-1, 0]: [1, 0],
    "back":  userId == 1 ? [1, 0]: [-1, 0],
    "left": userId == 1 ? [0, -1] : [0, 1],
    "right": userId == 1 ?  [0, 1] : [0, -1],
    "forward-left": userId == 1 ?  [-1, -1] : [1, 1],
    "forward-right":  userId == 1 ? [-1, 1] : [1, -1],
    "back-left": userId == 1 ?  [1, -1]: [-1, 1],
    "back-right": userId == 1 ?  [1, 1]: [-1, -1],
  };

  const maxRange = 7;

  for (const dir in movement) {
    const vector = directions[dir];
    if (!vector) continue;

    const range = movement[dir] === 'any' ? maxRange : movement[dir];

    for (let step = 1; step <= range; step++) {
      const nx = x + vector[0] * step;
      const ny = y + vector[1] * step;
      if (nx < 0 || nx >= 7 || ny < 0 || ny >= 7) break;

      const cell = document.querySelector(`.cell[data-x="${nx}"][data-y="${ny}"]`);
      if (!cell) break;

      const overlay = cell.querySelector('.cell-overlay');
      const occupant = board[nx][ny];
      if (occupant) {
        if (occupant.owner !== userId) {
          overlay.classList.add(userId === '1' ? 'can-attack-blue' : 'can-attack-orange');
        }
        break;
      }

      overlay.classList.add(userId === '1' ? 'can-move-blue' : 'can-move-orange');
    }
  }
}


function clearMoveHighlights() {
  document.querySelectorAll('.cell-overlay').forEach(overlay => {
    overlay.className = 'cell-overlay'; // Reset all
  });
}


function handleClick(x, y, cell) {
  const hand = userId === '1' ? hand1 : hand2;
  const selectedCard = hand[selectedHandIndex];

  // 🖐 Card in hand is selected
  if (selectedHandIndex !== null) {
    if (!selectedCard) return;

    if (selectedCard.mana > mana[userId]) {
      notify("red", "Not enough mana to use this card.");
      return;
    }

    if (selectedCard.type === 'monster') {
      const validCols = [0, 3, 6];
      const summonRow = userId === '1' ? 6 : 0;

      if (x === summonRow && validCols.includes(y)) {
        confirmAction(
          `Spend ${selectedCard.mana} mana to summon ${selectedCard.name}?`,
          "Yes, summon!",
          "Cancel",
          () => {
            ws.send(JSON.stringify({
              type: 'summon',
              user_id: userId,
              slot: selectedHandIndex,
              to: [x, y]
            }));
            selectedHandIndex = null;
            clearMoveHighlights();
          }
        );
      } else {
        notify("yellow", "Invalid summon position.");
      }

    } else if (selectedCard.type === 'sorcery') {
      // 👇 Full board activation allowed
      confirmAction(
        `Spend ${selectedCard.mana} mana to activate ${selectedCard.name} on this tile?`,
        "Activate!",
        "Cancel",
        () => {
          ws.send(JSON.stringify({
            type: 'activate-sorcery',
            user_id: userId,
            slot: selectedHandIndex,
            pos: [x, y]
          }));
          selectedHandIndex = null;
          clearMoveHighlights();
        }
      );
    }

    return;
  }

  // 🧭 Board click (after selection)
  if (userId !== turn) return notify('red', 'Not your turn!');

  const card = board[x][y];

  if (selected) {
    const from = selected;
    const to = [x, y];
    ws.send(JSON.stringify({
      type: 'move',
      from,
      to,
      user_id: userId
    }));
    selected = null;
    clearMoveHighlights();
  } else {
    if (card && card.owner === userId) {
      const backRow = userId === '1' ? 0 : 6;

      // 👊 Direct attack
      if (x === backRow) {
        confirmAction(
          `Attack directly with ${card.name} and deal ${card.mana} damage?`,
          "Attack!",
          "Cancel",
          () => {
            ws.send(JSON.stringify({
              type: 'direct-attack',
              user_id: userId,
              pos: [x, y]
            }));
            
            selected = null;
          }, () => {
            selected = [x, y];
            cell.classList.add('selected');
            highlightMoves(x, y, card);
          }
        );
        return;
      }

      selected = [x, y];
      cell.classList.add('selected');
      highlightMoves(x, y, card);
    } else if (cell.innerText) {
      notify('red', 'Not your card');
    } else {
      notify('red', 'Please select a card');
    }
  }
}

function highlightSorceryZones() {
  clearMoveHighlights();

  const hand = userId === '1' ? hand1 : hand2;
  const card = hand[selectedHandIndex];
  if (!card || !Array.isArray(card.activation_needs)) return;

  const directions = {
    "forward": userId === '1' ? [-1, 0] : [1, 0],
    "back": userId === '1' ? [1, 0] : [-1, 0],
    "left": userId === '1' ? [0, -1] : [0, 1],
    "right": userId === '1' ? [0, 1] : [0, -1],
    "forward-left": userId === '1' ? [-1, -1] : [1, 1],
    "forward-right": userId === '1' ? [-1, 1] : [1, -1],
    "back-left": userId === '1' ? [1, -1] : [-1, 1],
    "back-right": userId === '1' ? [1, 1] : [-1, -1]
  };

  const flipDirection = {
    "forward": "back",
    "back": "forward",
    "left": "right",
    "right": "left",
    "forward-left": "back-right",
    "forward-right": "back-left",
    "back-left": "forward-right",
    "back-right": "forward-left"
  };

  for (let x = 0; x < board.length; x++) {
    for (let y = 0; y < board[0].length; y++) {
      let satisfiesAll = true;

      for (const dir of card.activation_needs) {
        const [dx, dy] = directions[dir];
        const tx = x + dx;
        const ty = y + dy;

        // 👇 Skip out-of-bounds
        if (tx < 0 || tx >= 7 || ty < 0 || ty >= 7) {
          satisfiesAll = false;
          break;
        }

        const neighbor = board[tx][ty];
        if (!neighbor || neighbor.type !== 'monster') {
          satisfiesAll = false;
          break;
        }

        // 👇 Flip direction based on who owns the monster
        const baseOpposite = flipDirection[dir];
        const effectiveDir = neighbor.owner === userId ? baseOpposite : flipDirection[baseOpposite];

        const movementVal = neighbor.movement?.[effectiveDir];
        if (movementVal !== 1 && movementVal !== 'any') {
          satisfiesAll = false;
          break;
        }
      }

      if (satisfiesAll) {
        const cell = document.querySelector(`.cell[data-x="${x}"][data-y="${y}"]`);
        if (cell) {
          const overlay = cell.querySelector('.cell-overlay');
          overlay.classList.add(userId === '1' ? 'can-move-blue' : 'can-move-orange');
        }
      }
    }
  }
}





function notify(color, message) {
  const container = document.getElementById('notification-container');
  const note = document.createElement('div');
  note.className = `notification ${color}`;
  note.textContent = message;

  container.appendChild(note);

  setTimeout(() => {
    note.remove();
  }, 3000); // Clean up after animation
}

function confirmAction(message, yesMessage, noMessage, onYes, onNo = () => {}) {
  const overlay = document.getElementById('confirmation-overlay');
  const messageEl = document.getElementById('confirmation-message');
  const yesBtn = document.getElementById('confirm-yes');
  const noBtn = document.getElementById('confirm-no');
  yesBtn.innerText = yesMessage;
  noBtn.innerText = noMessage;

  messageEl.textContent = message;
  overlay.style.display = 'flex';

  const cleanup = () => {
    overlay.style.display = 'none';
    yesBtn.onclick = null;
    noBtn.onclick = null;
  };

  yesBtn.onclick = () => {
    cleanup();
    onYes();
  };

  noBtn.onclick = () => {
    cleanup();
    onNo();
  };
}



document.addEventListener('contextmenu', (e) => {
  e.preventDefault(); // prevent browser context menu

  // Clear selection
  selected = null;
  selectedHandIndex = null;

  // Clear visual highlights
  clearMoveHighlights();
  document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
  document.querySelectorAll('.summon-zone').forEach(el => el.classList.remove('summon-zone'));
});
